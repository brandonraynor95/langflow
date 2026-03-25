from __future__ import annotations

import asyncio
import os
import uuid
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage

from lfx.base.agents.events import (
    TOOL_EVENT_HANDLERS,
    _calculate_duration,
    _extract_output_text,
)
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, MessageInput, MessageTextInput, MultilineInput, StrInput
from lfx.io import BoolInput, IntInput, Output
from lfx.log.logger import logger
from lfx.memory import aget_messages
from lfx.schema.content_block import ContentBlock
from lfx.schema.content_types import TextContent
from lfx.schema.message import Message
from lfx.schema.properties import Properties
from lfx.utils.constants import MESSAGE_SENDER_AI

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from lfx.schema.log import OnTokenFunctionType

_DEFAULT_WORKSPACE = os.path.join(os.path.expanduser("~"), "deepagent-workspace")


class DeepAgentComponent(Component):
    """A Langflow component that wraps LangChain's Deep Agents SDK."""

    display_name: str = "Deep Agent"
    description: str = (
        "Run a Deep Agent (LangChain's agent harness built on LangGraph). "
        "Connect a language model and optional tools, then set instructions "
        "to guide the agent's behaviour."
    )
    documentation: str = "https://docs.langchain.com/oss/python/deepagents/overview"
    icon = "bot"
    name = "DeepAgent"

    inputs = [
        # ── Core ──────────────────────────────────────────────────────────
        HandleInput(
            name="llm",
            display_name="Language Model",
            input_types=["LanguageModel"],
            required=True,
            info="Connect a Language Model component. The model must support tool calling.",
        ),
        HandleInput(
            name="tools",
            display_name="Tools",
            input_types=["Tool"],
            is_list=True,
            required=False,
            info="Tools the agent can use to complete tasks.",
        ),
        MessageInput(
            name="input_value",
            display_name="Input",
            info="The user message or task for the agent to process.",
            tool_mode=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name="Agent Instructions",
            info="Custom instructions prepended before the Deep Agent base prompt.",
            value="You are a helpful assistant that can use tools to answer questions and perform tasks.",
            advanced=False,
        ),
        # ── Chat history ──────────────────────────────────────────────────
        IntInput(
            name="n_messages",
            display_name="Number of Chat History Messages",
            value=100,
            info="Number of past conversation messages to include as chat history. Set to 0 to disable.",
            advanced=True,
        ),
        MessageTextInput(
            name="context_id",
            display_name="Context ID",
            info="Optional extra key to scope the chat history lookup.",
            value="",
            advanced=True,
        ),
        # ── Workspace / Backend ───────────────────────────────────────────
        BoolInput(
            name="use_local_filesystem",
            display_name="Use Local Filesystem Sandbox",
            value=False,
            advanced=True,
            info=(
                "When enabled the agent reads/writes real files and can execute shell commands "
                "inside the Workspace Directory. When disabled all file operations are ephemeral "
                "(stored in LangGraph state only)."
            ),
        ),
        StrInput(
            name="workspace_dir",
            display_name="Workspace Directory",
            value=_DEFAULT_WORKSPACE,
            advanced=True,
            info=(
                "Root directory for the local filesystem sandbox. "
                f"Defaults to {_DEFAULT_WORKSPACE!r}. Only used when 'Use Local Filesystem Sandbox' is on."
            ),
        ),
        # ── Context Engineering – Long-term memory (AGENTS.md) ───────────
        BoolInput(
            name="enable_memory_files",
            display_name="Enable AGENTS.md Memory",
            value=False,
            advanced=True,
            info=(
                "Load one or more AGENTS.md files at startup and inject their content into the "
                "system prompt so the agent always has project-specific context. "
                "Requires 'Use Local Filesystem Sandbox' to be enabled."
            ),
        ),
        StrInput(
            name="memory_paths",
            display_name="Memory File Paths",
            value="",
            advanced=True,
            info=(
                "Comma-separated paths to AGENTS.md files (e.g. "
                "'/workspace/AGENTS.md, ~/.deepagents/AGENTS.md'). "
                "Only used when 'Enable AGENTS.md Memory' is on."
            ),
        ),
        # ── Context Engineering – Skills ──────────────────────────────────
        BoolInput(
            name="enable_skills",
            display_name="Enable Skills",
            value=False,
            advanced=True,
            info=(
                "Load agent skills from the filesystem. Skills are directories containing "
                "a SKILL.md file with YAML front-matter describing on-demand workflows. "
                "Requires 'Use Local Filesystem Sandbox' to be enabled."
            ),
        ),
        StrInput(
            name="skills_paths",
            display_name="Skills Source Paths",
            value="",
            advanced=True,
            info=(
                "Comma-separated paths to skill source directories "
                "(e.g. '/workspace/skills, ~/.deepagents/skills'). "
                "Only used when 'Enable Skills' is on."
            ),
        ),
        # ── Agent internals ───────────────────────────────────────────────
        BoolInput(
            name="verbose",
            display_name="Verbose",
            value=False,
            advanced=True,
            info="Log extra debug information.",
        ),
        IntInput(
            name="max_iterations",
            display_name="Max Iterations",
            value=15,
            advanced=True,
            info="Maximum number of agent steps before stopping.",
        ),
        IntInput(
            name="recursion_limit",
            display_name="Recursion Limit",
            advanced=True,
            info="LangGraph recursion limit. 0 = use Deep Agent default (1000).",
            value=0,
            required=False,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Response", method="message_response"),
    ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_input_text(self) -> str:
        if isinstance(self.input_value, Message):
            lc_msg = self.input_value.to_lc_message()
            content = getattr(lc_msg, "content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [item.get("text", "") for item in content if item.get("type") == "text"]
                return " ".join(parts)
            return str(content)
        return str(self.input_value or "")

    def _unwrap_messages(self, messages: Any) -> list[BaseMessage]:
        """Unwrap LangGraph ``Overwrite`` containers and return a plain list."""
        try:
            from langgraph.types import Overwrite as LGOverwrite

            if isinstance(messages, LGOverwrite):
                messages = messages.value
        except ImportError:
            pass
        return messages if isinstance(messages, list) else []

    def _last_ai_text(self, messages: Any) -> str:
        """Return the text of the last AIMessage in *messages*."""
        for msg in reversed(self._unwrap_messages(messages)):
            if isinstance(msg, AIMessage):
                content = msg.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    return " ".join(filter(None, parts))
                return str(content)
        return ""

    async def _get_chat_history(self, session_id: str) -> list[BaseMessage]:
        """Fetch past session messages from the Langflow store."""
        try:
            n = int(getattr(self, "n_messages", 100) or 100)
            if n == 0:
                return []
            context_id = getattr(self, "context_id", "") or None
            # Fetch a large window then slice so we always get the most recent N
            stored = await aget_messages(
                session_id=session_id,
                context_id=context_id,
                limit=10000,
                order="ASC",
            )
            # Take the most recent n messages (list is already ASC = oldest first)
            if n:
                stored = stored[-n:]
            lc_messages: list[BaseMessage] = []
            current_input_id = getattr(self.input_value, "id", None)
            for item in stored:
                if not isinstance(item, Message):
                    continue
                # Skip the current user turn to avoid echoing it back
                if current_input_id and getattr(item, "id", None) == current_input_id:
                    continue
                try:
                    lc_messages.append(item.to_lc_message())
                except Exception:  # noqa: BLE001
                    pass
            return lc_messages
        except Exception as exc:  # noqa: BLE001
            await logger.adebug(f"DeepAgent: chat history retrieval failed: {exc}")
            return []

    def _build_backend(self) -> Any:
        """Return the appropriate deepagents backend instance/factory."""
        use_local = bool(getattr(self, "use_local_filesystem", False))
        if not use_local:
            from deepagents.backends import StateBackend

            return StateBackend  # factory – deepagents calls it as StateBackend(runtime)

        workspace = str(getattr(self, "workspace_dir", "") or _DEFAULT_WORKSPACE).strip()
        os.makedirs(workspace, exist_ok=True)
        from deepagents.backends import LocalShellBackend

        return LocalShellBackend(root_dir=workspace)

    def _parse_paths(self, attr: str) -> list[str]:
        raw = str(getattr(self, attr, "") or "").strip()
        return [p.strip() for p in raw.split(",") if p.strip()] if raw else []

    def _build_deep_agent(self, llm: BaseChatModel, tools: list[BaseTool]) -> Any:
        """Instantiate and return a compiled Deep Agent graph."""
        try:
            from deepagents import create_deep_agent
        except ImportError as exc:
            msg = "The 'deepagents' package is required. Install it with: pip install deepagents"
            raise ImportError(msg) from exc

        backend = self._build_backend()

        kwargs: dict[str, Any] = {
            "model": llm,
            "tools": tools or [],
            "backend": backend,
        }

        system_prompt = str(getattr(self, "system_prompt", "") or "").strip()
        if system_prompt:
            kwargs["system_prompt"] = system_prompt

        # Long-term memory (AGENTS.md files)
        if getattr(self, "enable_memory_files", False):
            paths = self._parse_paths("memory_paths")
            if paths:
                kwargs["memory"] = paths

        # Skills
        if getattr(self, "enable_skills", False):
            paths = self._parse_paths("skills_paths")
            if paths:
                kwargs["skills"] = paths

        return create_deep_agent(**kwargs)

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------

    async def _handle_subagent_start(
        self,
        event: dict[str, Any],
        agent_message: Message,
        send_message_callback: Any,
        start_time: float,
    ) -> tuple[Message, float]:
        """Add a visual entry in Agent Steps when a subagent starts."""
        name = event.get("name", "subagent")
        metadata = event.get("metadata", {})
        # Only annotate events that look like a subagent call (nested LangGraph)
        if metadata.get("langgraph_node") and metadata.get("langgraph_step"):
            if not agent_message.content_blocks:
                agent_message.content_blocks = [ContentBlock(title="Agent Steps", contents=[])]
            duration = _calculate_duration(start_time)
            text_content = TextContent(
                type="text",
                text=f"Starting subagent: **{name}**",
                duration=duration,
                header={"title": f"Subagent: {name}", "icon": "Bot"},
            )
            agent_message.content_blocks[0].contents.append(text_content)
            agent_message = await send_message_callback(message=agent_message, skip_db_update=True)
            start_time = perf_counter()
        return agent_message, start_time

    # ------------------------------------------------------------------
    # Output method
    # ------------------------------------------------------------------

    async def message_response(self) -> Message:
        llm: BaseChatModel = self.llm
        if llm is None:
            msg = "No language model connected. Please attach a Language Model component."
            raise ValueError(msg)

        tools: list[BaseTool] = self.tools or []
        input_text = self._get_input_text()
        if not input_text.strip():
            input_text = "Continue the conversation."

        agent = self._build_deep_agent(llm, tools)

        # Session / sender setup
        session_id: str | None = None
        if hasattr(self, "graph") and self.graph:
            session_id = str(self.graph.session_id)
        elif hasattr(self, "_session_id") and self._session_id:
            session_id = str(self._session_id)

        # Retrieve chat history
        chat_history: list[BaseMessage] = []
        if session_id:
            chat_history = await self._get_chat_history(session_id)

        sender_name = self.display_name or "Deep Agent"
        agent_message = Message(
            sender=MESSAGE_SENDER_AI,
            sender_name=sender_name,
            properties=Properties(icon="Bot", state="partial"),
            content_blocks=[ContentBlock(title="Agent Steps", contents=[])],
            session_id=session_id or str(uuid.uuid4()),
        )

        # Token streaming callback
        on_token_callback: OnTokenFunctionType | None = None
        if self._event_manager:
            on_token_callback = cast("OnTokenFunctionType", self._event_manager.on_token)

        # Persist the initial partial message to get a stable ID
        agent_message = await self.send_message(agent_message)
        initial_message_id = agent_message.get_id()

        # Invocation payload – history + current user turn
        invoke_input: dict[str, Any] = {
            "messages": [*chat_history, HumanMessage(content=input_text)],
        }

        # Optional LangGraph config
        config: dict[str, Any] = {}
        recursion_limit = int(getattr(self, "recursion_limit", 0) or 0)
        if recursion_limit > 0:
            config["recursion_limit"] = recursion_limit

        tool_blocks_map: dict[str, Any] = {}
        start_time = perf_counter()
        last_messages_output: list[BaseMessage] | None = None
        accumulated_text = ""

        try:
            stream_kwargs: dict[str, Any] = {"version": "v2"}
            if config:
                stream_kwargs["config"] = config

            async for event in agent.astream_events(invoke_input, **stream_kwargs):
                event_type: str = event["event"]

                # Tool events ─────────────────────────────────────────────
                if event_type in TOOL_EVENT_HANDLERS:
                    agent_message, start_time = await TOOL_EVENT_HANDLERS[event_type](
                        event, agent_message, tool_blocks_map, self.send_message, start_time
                    )

                # LLM token streaming ─────────────────────────────────────
                elif event_type == "on_chat_model_stream":
                    data_chunk = event["data"].get("chunk")
                    if isinstance(data_chunk, AIMessageChunk):
                        token = _extract_output_text(data_chunk.content)
                        if token:
                            accumulated_text += token
                            if on_token_callback and initial_message_id:
                                await asyncio.to_thread(
                                    on_token_callback,
                                    data={"chunk": token, "id": str(initial_message_id)},
                                )
                        if not agent_message.text:
                            start_time = perf_counter()

                # Subagent chain start ─────────────────────────────────────
                elif event_type == "on_chain_start":
                    agent_message, start_time = await self._handle_subagent_start(
                        event, agent_message, self.send_message, start_time
                    )

                # LangGraph final state (chain end with messages) ──────────
                elif event_type == "on_chain_end":
                    data_output = event["data"].get("output")
                    if isinstance(data_output, dict) and "messages" in data_output:
                        msgs = self._unwrap_messages(data_output["messages"])
                        if msgs:
                            last_messages_output = msgs
                            final_text = self._last_ai_text(msgs)
                            if final_text and agent_message.content_blocks:
                                duration = _calculate_duration(start_time)
                                agent_message.content_blocks[0].contents.append(
                                    TextContent(
                                        type="text",
                                        text=final_text,
                                        duration=duration,
                                        header={"title": "Output", "icon": "MessageSquare"},
                                    )
                                )
                            start_time = perf_counter()

        except Exception as exc:
            await logger.aerror(f"Deep Agent streaming error: {exc}")
            raise

        # Resolve final text
        response_text = (
            self._last_ai_text(last_messages_output)
            if last_messages_output
            else accumulated_text
        ) or "(No response)"

        if self.verbose:
            await logger.adebug(f"Deep Agent response: {response_text[:500]}")

        agent_message.text = response_text
        agent_message.properties.state = "complete"
        agent_message = await self.send_message(agent_message)
        self.status = agent_message
        return agent_message
