"""TranslationFlow - Language Detection, Translation, and Intent Classification.

This flow translates user input to English and classifies intent as either
'generate_component' or 'question'.

Usage:
    from langflow.agentic.flows.translation_flow import get_graph
    graph = await get_graph(provider="OpenAI", model_name="gpt-4o-mini")
"""

from lfx.components.input_output import ChatInput, ChatOutput
from lfx.components.models import LanguageModelComponent
from lfx.graph import Graph

from langflow.agentic.flows.model_config import build_model_config as _build_model_config

TRANSLATION_PROMPT = """You are a Language Detection, Translation, and Intent Classification \
Agent for Langflow Assistant.

Your responsibilities are:
1. Translate the input text to English (if not already in English)
2. Classify the user's intent

Intent Classification:
- "generate_component": User wants you to CREATE/BUILD/GENERATE/MODIFY a custom Langflow component.
  This includes both new component requests AND follow-up modifications to a previous component.
  Examples: "Create a component that calls an API", "Build me a custom component for...",
  "can you use dataframe output instead?", "add error handling", "make it also support CSV",
  "change the output to return a list", "use requests instead of urllib", "add a timeout parameter"
- "build_flow": User wants to BUILD/CREATE/MODIFY a flow, EDIT component settings,
  or is asking questions ABOUT THEIR CURRENT FLOW (what it does, inspect fields, diagnose).
  This includes ANY request to change, update, or inspect specific component parameters.
  Examples: "Build me a RAG pipeline", "Create a chatbot flow", "Make a flow that...",
  "Set up an agent with tools", "Build a flow that takes input and sends to OpenAI",
  "can you build a flow for me", "simple chat flow", "make a simple chatbot",
  "build me a flow", "create a flow",
  "change the model to X", "set the temperature to Y", "update the system prompt",
  "what does this flow do", "what's in my flow", "check my flow",
  "find the value in", "what's configured", "diagnose my flow"
- "question": User is ASKING A QUESTION, seeking help, or wants information.
  Examples: "How do I create a component?", "What is a component?", "Can you explain...", "How to use..."

IMPORTANT rules:
- "How to create a component" = question (asking for guidance)
- "Create a component that does X" = generate_component (requesting creation of a single component)
- "Build a flow that does X" = build_flow (requesting creation of a multi-component workflow)
- "Create a RAG pipeline" = build_flow (pipeline = flow)
- "Create a chatbot" = build_flow (chatbot = flow with multiple components)
- "simple chat flow" = build_flow (describing a flow to build)
- "can you build a flow" = build_flow (requesting flow creation)
- "change the model to X" = build_flow (editing a component setting)
- "set the temperature" = build_flow (editing a component setting)
- "what does this flow do" = build_flow (inspecting the current flow)
- When in doubt between build_flow and question for flow-related requests, prefer build_flow
- Short follow-up requests that imply changes to something previously generated = generate_component
  (e.g., "use X instead", "add Y", "change Z", "make it do W", "can you also...", "what about using...")

Output format (JSON only, no markdown):
{{"translation": "<english text>", "intent": "<generate_component|build_flow|question>"}}

Examples:
Input: "como criar um componente no langflow"
Output: {{"translation": "how to create a component in langflow", "intent": "question"}}

Input: "crie um componente que chama uma API"
Output: {{"translation": "create a component that calls an API", "intent": "generate_component"}}

Input: "what is the best way to build flows?"
Output: {{"translation": "what is the best way to build flows?", "intent": "question"}}

Input: "make me a component that parses JSON"
Output: {{"translation": "make me a component that parses JSON", "intent": "generate_component"}}

Input: "build me a RAG pipeline"
Output: {{"translation": "build me a RAG pipeline", "intent": "build_flow"}}

Input: "create a chatbot flow with OpenAI"
Output: {{"translation": "create a chatbot flow with OpenAI", "intent": "build_flow"}}

Input: "can you build a flow for me?"
Output: {{"translation": "can you build a flow for me?", "intent": "build_flow"}}

Input: "simple chat flow"
Output: {{"translation": "simple chat flow", "intent": "build_flow"}}

Input: "change the model to gpt-4o-mini"
Output: {{"translation": "change the model to gpt-4o-mini", "intent": "build_flow"}}

Input: "set the temperature to 0.5"
Output: {{"translation": "set the temperature to 0.5", "intent": "build_flow"}}

Input: "what does this flow do?"
Output: {{"translation": "what does this flow do?", "intent": "build_flow"}}

Input: "can you use dataframe output instead?"
Output: {{"translation": "can you use dataframe output instead?", "intent": "generate_component"}}

Input: "add a retry mechanism with exponential backoff"
Output: {{"translation": "add a retry mechanism with exponential backoff", "intent": "generate_component"}}

Input: "what does the output format look like?"
Output: {{"translation": "what does the output format look like?", "intent": "question"}}
"""


def get_graph(
    provider: str | None = None,
    model_name: str | None = None,
    api_key_var: str | None = None,
) -> Graph:
    """Create and return the TranslationFlow graph.

    Args:
        provider: Model provider (e.g., "OpenAI", "Anthropic"). Defaults to OpenAI.
        model_name: Model name (e.g., "gpt-4o-mini"). Defaults to gpt-4o-mini.
        api_key_var: Optional API key variable name (e.g., "OPENAI_API_KEY").

    Returns:
        Graph: The configured translation flow graph.
    """
    # Use defaults if not provided
    provider = provider or "OpenAI"
    model_name = model_name or "gpt-4o-mini"

    # Create chat input component
    chat_input = ChatInput()
    chat_input.set(
        sender="User",
        sender_name="User",
        should_store_message=False,
    )

    # Create language model component
    llm = LanguageModelComponent()

    # Set model configuration
    llm.set_input_value("model", _build_model_config(provider, model_name))

    # Configure LLM
    llm_config = {
        "input_value": chat_input.message_response,
        "system_message": TRANSLATION_PROMPT,
        "temperature": 0.1,  # Low temperature for consistent JSON output
    }

    if api_key_var:
        llm_config["api_key"] = api_key_var

    llm.set(**llm_config)

    # Create chat output component
    chat_output = ChatOutput()
    chat_output.set(
        input_value=llm.text_response,
        sender="Machine",
        sender_name="AI",
        should_store_message=False,
        clean_data=True,
        data_template="{text}",
    )

    return Graph(start=chat_input, end=chat_output)
