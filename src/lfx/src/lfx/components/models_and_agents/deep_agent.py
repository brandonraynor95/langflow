from __future__ import annotations

import asyncio
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
from lfx.inputs.inputs import HandleInput, MessageInput, MessageTextInput, MultilineInput
from lfx.io import BoolInput, IntInput, Output
from lfx.log.logger import logger
from lfx.memory import aget_messages
from lfx.schema.content_block import ContentBlock
from lfx.schema.content_types import TextContent
from lfx.schema.data import Data
from lfx.schema.message import Message
from lfx.schema.properties import Properties
from lfx.utils.constants import MESSAGE_SENDER_AI

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from lfx.schema.log import OnTokenFunctionType


class DeepAgentComponent(Component):
    """A Langflow component that wraps LangChain's Deep Agents SDK.

    Deep Agents is an agent harness built on LangGraph that supports
    planning, context management via a virtual filesystem, subagent
    spawning, and long-term memory out of the box.

    Reference: https://docs.langchain.com/oss/python/deepagents/overview
    """

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
            info="System prompt that guides the agent's behaviour.",
            value="You are a helpful assistant that can use tools to answer questions and perform tasks.",
            advanced=False,
        ),
        BoolInput(
            name="verbose",
            display_name="Verbose",
            value=False,
            advanced=True,
            info="Enable verbose logging of agent steps.",
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
            info="LangGraph recursion limit. Set to 0 to use the Deep Agent default (100).",
            value=0,
            required=False,
        ),
        IntInput(
            name="n_messages",
            display_name="Number of Chat History Messages",
            value=100,
            info="Number of past messages to include as chat history.",
            advanced=True,
        ),
        MessageTextInput(
            name="context_id",
            display_name="Context ID",
            info="Extra context key to scope the chat history.",
            value="",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Response", method="message_response"),
    ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_input_text(self) -> str:
        """Extract plain text from the input value."""
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

    def _last_ai_text(self, messages: Any) -> str:
        """Return the text content of the last AIMessage in *messages*.

        Handles LangGraph ``Overwrite`` wrappers transparently.
        """
        try:
            from langgraph.types import Overwrite as LGOverwrite

            if isinstance(messages, LGOverwrite):
                messages = messages.value
        except ImportError:
            pass

        if not isinstance(messages, list):
            return ""

        for msg in reversed(messages):
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
                    return " ".join(parts)
                return str(content)
        return ""

    async def _get_chat_history(self, session_id: str) -> list[BaseMessage]:
        """Retrieve past messages from the Langflow store as LangChain messages."""
        try:
            n = int(getattr(self, "n_messages", 100) or 100)
            context_id = getattr(self, "context_id", "") or ""
            stored: list[Data] = await aget_messages(
                session_id=session_id,
                sender=None,
                sender_name=None,
                limit=n,
                order="ASC",
                flow_id=self.graph.flow_id if hasattr(self, "graph") and self.graph else None,
            )
            lc_messages: list[BaseMessage] = []
            for item in stored:
                if not isinstance(item, Message):
                    item = Message(**item.data) if hasattr(item, "data") else None
                if item is None:
                    continue
                # Skip the current input message to avoid duplication
                if getattr(item, "id", None) == getattr(self.input_value, "id", None):
                    continue
                try:
                    lc_messages.append(item.to_lc_message())
                except Exception:  # noqa: BLE001
                    pass
            return lc_messages
        except Exception as exc:  # noqa: BLE001
            await logger.adebug(f"DeepAgent: could not retrieve chat history: {exc}")
            return []

    def _build_deep_agent(self, llm: BaseChatModel, tools: list[BaseTool]) -> Any:
        """Instantiate and return a Deep Agent compiled graph."""
        try:
            from deepagents import create_deep_agent
        except ImportError as exc:
            msg = (
                "The 'deepagents' package is required. "
                "Install it with: pip install deepagents"
            )
            raise ImportError(msg) from exc

        kwargs: dict[str, Any] = {
            "model": llm,
            "tools": tools or [],
        }

        system_prompt = getattr(self, "system_prompt", "") or ""
        if system_prompt.strip():
            kwargs["system_prompt"] = system_prompt

        return create_deep_agent(**kwargs)

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

        # Determine session id
        session_id: str | None = None
        if hasattr(self, "graph") and self.graph:
            session_id = str(self.graph.session_id)
        elif hasattr(self, "_session_id") and self._session_id:
            session_id = str(self._session_id)

        # Retrieve chat history so the agent has conversation context
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

        # Token callback for live streaming to the playground
        on_token_callback: OnTokenFunctionType | None = None
        if self._event_manager:
            on_token_callback = cast("OnTokenFunctionType", self._event_manager.on_token)

        # Send initial partial message so the frontend gets a message id to stream into
        agent_message = await self.send_message(agent_message)
        initial_message_id = agent_message.get_id()

        # Build the invocation payload (prepend history so agent has context)
        invoke_input: dict[str, Any] = {
            "messages": [*chat_history, HumanMessage(content=input_text)],
        }

        # Build LangGraph config
        config: dict[str, Any] = {}
        recursion_limit = getattr(self, "recursion_limit", 0) or 0
        if isinstance(recursion_limit, int) and recursion_limit > 0:
            config["recursion_limit"] = recursion_limit

        tool_blocks_map: dict[str, Any] = {}
        start_time = perf_counter()
        last_messages_output: list[BaseMessage] | None = None
        accumulated_text = ""

        try:
            event_stream = agent.astream_events(invoke_input, version="v2", config=config or None)
            async for event in event_stream:
                event_type: str = event["event"]

                # ---- Tool events (start / end / error) -------------------
                if event_type in TOOL_EVENT_HANDLERS:
                    tool_handler = TOOL_EVENT_HANDLERS[event_type]
                    agent_message, start_time = await tool_handler(
                        event, agent_message, tool_blocks_map, self.send_message, start_time
                    )

                # ---- Streaming token from the LLM ------------------------
                elif event_type == "on_chat_model_stream":
                    data_chunk = event["data"].get("chunk")
                    if isinstance(data_chunk, AIMessageChunk):
                        output_text = _extract_output_text(data_chunk.content)
                        if output_text:
                            accumulated_text += output_text
                            if on_token_callback and initial_message_id:
                                await asyncio.to_thread(
                                    on_token_callback,
                                    data={
                                        "chunk": output_text,
                                        "id": str(initial_message_id),
                                    },
                                )
                        if not agent_message.text:
                            start_time = perf_counter()

                # ---- LangGraph chain end: capture messages output --------
                elif event_type == "on_chain_end":
                    data_output = event["data"].get("output")
                    if isinstance(data_output, dict) and "messages" in data_output:
                        raw_msgs = data_output["messages"]
                        # Unwrap LangGraph Overwrite wrapper if present
                        try:
                            from langgraph.types import Overwrite as LGOverwrite

                            if isinstance(raw_msgs, LGOverwrite):
                                raw_msgs = raw_msgs.value
                        except ImportError:
                            pass
                        if isinstance(raw_msgs, list):
                            last_messages_output = raw_msgs
                        # Add output text block to Agent Steps if present
                        final_text = self._last_ai_text(last_messages_output or [])
                        if final_text and agent_message.content_blocks:
                            duration = _calculate_duration(start_time)
                            text_content = TextContent(
                                type="text",
                                text=final_text,
                                duration=duration,
                                header={"title": "Output", "icon": "MessageSquare"},
                            )
                            agent_message.content_blocks[0].contents.append(text_content)
                        start_time = perf_counter()

        except Exception as e:
            await logger.aerror(f"Deep Agent streaming error: {e}")
            raise

        # Determine final response text
        response_text = ""
        if last_messages_output:
            response_text = self._last_ai_text(last_messages_output)
        if not response_text:
            response_text = accumulated_text
        if not response_text:
            response_text = "(No response)"

        if self.verbose:
            await logger.adebug(f"Deep Agent response: {response_text[:500]}")

        agent_message.text = response_text
        agent_message.properties.state = "complete"

        # Final DB persist
        agent_message = await self.send_message(agent_message)
        self.status = agent_message
        return agent_message
