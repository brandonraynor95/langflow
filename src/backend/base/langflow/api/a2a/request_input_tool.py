"""Long-running tool support for A2A INPUT_REQUIRED signaling.

Follows the Google ADK pattern: the developer marks a tool as
"long-running." When the LLM calls it, the tool returns immediately
with a pending status. The A2A framework detects this and transitions
the task to input-required. Execution completes normally — no
suspended coroutines.

When the client responds, a new flow execution starts with the
response injected, using the same session_id for conversation
continuity.

Two mechanisms are supported:

1. Auto-injected request_input tool (for Agent components):
   The tool is injected into the Agent's toolkit during A2A execution.
   If the LLM calls it, the response is marked as pending and the
   framework transitions to input-required. If the LLM doesn't call
   it (common — LLMs prefer to type out questions), execution completes
   normally as a single turn.

2. Flow output detection (for any flow):
   If the flow's output contains a pending marker (set by a future
   RequestInput canvas component), the A2A adapter detects it and
   transitions to input-required. This is the primary mechanism.
"""

from __future__ import annotations

from langflow.api.a2a.task_manager import TaskManager

# Marker that signals the A2A adapter to transition to input-required.
# When a tool returns a dict containing this key with value True,
# the adapter knows execution should pause for client input.
INPUT_REQUIRED_MARKER = "__a2a_input_required__"


def create_request_input_tool(
    task_id: str,
    task_manager: TaskManager,
    timeout_seconds: float = 300.0,
) -> dict:
    """Create a request_input tool for A2A agent execution.

    The tool returns immediately with a pending response (no suspension).
    The A2A adapter checks the flow output for the INPUT_REQUIRED_MARKER
    and transitions the task accordingly.

    Returns a dict with:
    - name: str — tool name
    - description: str — guidance for the LLM
    - handler: async callable(question: str) -> str
    """

    async def request_input_handler(question: str) -> str:
        """Ask the calling agent for clarification.

        Returns a marked response that the A2A framework will detect
        and convert into an input-required task state.
        """
        # Mark the task as input-required with the question
        await task_manager.set_input_required(task_id, question)

        # Return a response that signals the framework
        return f"{INPUT_REQUIRED_MARKER}:{question}"

    return {
        "name": "request_input",
        "description": (
            "IMPORTANT: Use this tool to ask the user or calling agent for "
            "clarification or missing information. When you need additional "
            "details to complete a task, call this tool with your question. "
            "The execution will pause until the user responds."
        ),
        "handler": request_input_handler,
    }


def is_input_required_response(text: str) -> bool:
    """Check if a flow's output text contains the input-required marker."""
    return isinstance(text, str) and INPUT_REQUIRED_MARKER in text


def extract_input_required_question(text: str) -> str:
    """Extract the question from an input-required marked response."""
    if INPUT_REQUIRED_MARKER in text:
        return text.split(f"{INPUT_REQUIRED_MARKER}:", 1)[-1].strip()
    return text


# Legacy exports for backward compatibility with existing tests
def resolve_input_request(event, response_holder, response):
    """Legacy — no longer used in the new pattern."""
    response_holder["response"] = response
    event.set()
