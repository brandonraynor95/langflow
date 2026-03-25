from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, MessageInput, MultilineInput
from lfx.io import BoolInput, IntInput, Output
from lfx.log.logger import logger
from lfx.schema.content_block import ContentBlock
from lfx.schema.message import Message
from lfx.schema.properties import Properties
from lfx.utils.constants import MESSAGE_SENDER_AI

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool


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

    def _last_ai_text(self, messages: list[BaseMessage]) -> str:
        """Return the text content of the last AIMessage in *messages*."""
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

        sender_name = self.display_name or "Deep Agent"
        agent_message = Message(
            sender=MESSAGE_SENDER_AI,
            sender_name=sender_name,
            properties=Properties(icon="Bot", state="partial"),
            content_blocks=[ContentBlock(title="Agent Steps", contents=[])],
            session_id=session_id or str(uuid.uuid4()),
        )

        # Build the invocation payload
        invoke_input: dict[str, Any] = {
            "messages": [HumanMessage(content=input_text)],
        }

        # Build LangGraph config
        config: dict[str, Any] = {}
        recursion_limit = getattr(self, "recursion_limit", 0) or 0
        if isinstance(recursion_limit, int) and recursion_limit > 0:
            config["recursion_limit"] = recursion_limit

        try:
            if config:
                result = await agent.ainvoke(invoke_input, config=config)
            else:
                result = await agent.ainvoke(invoke_input)
        except NotImplementedError:
            # Fallback to synchronous invoke if async not available
            import asyncio

            loop = asyncio.get_event_loop()
            if config:
                result = await loop.run_in_executor(None, lambda: agent.invoke(invoke_input, config=config))
            else:
                result = await loop.run_in_executor(None, lambda: agent.invoke(invoke_input))

        # Extract the AI response text from the result
        response_text = ""
        if isinstance(result, dict):
            messages_out = result.get("messages", [])
            if messages_out:
                response_text = self._last_ai_text(messages_out)
            if not response_text:
                # Fallback: check for structured_response key
                structured = result.get("structured_response")
                if structured is not None:
                    import json

                    try:
                        response_text = json.dumps(structured)
                    except (TypeError, ValueError):
                        response_text = str(structured)
        else:
            response_text = str(result)

        if not response_text:
            response_text = "(No response)"

        if self.verbose:
            await logger.adebug(f"Deep Agent response: {response_text[:500]}")

        agent_message.text = response_text
        agent_message.properties.state = "complete"

        await self.send_message(agent_message)
        self.status = agent_message
        return agent_message
