"""Auto-injected request_input tool for A2A INPUT_REQUIRED signaling.

When a flow is executed via A2A and contains an Agent component,
a request_input tool is automatically injected. The LLM autonomously
decides when to call it, triggering the INPUT_REQUIRED task state.

The tool uses asyncio.Event for suspension:
1. LLM calls request_input("Which environment?")
2. Handler sets task → INPUT_REQUIRED and awaits asyncio.Event
3. Client sends follow-up message
4. Router calls resolve_input_request() → event.set()
5. Handler returns client's response to the LLM
6. LLM continues reasoning
"""

from __future__ import annotations

import asyncio

from langflow.api.a2a.task_manager import TaskManager


def create_request_input_tool(
    task_id: str,
    task_manager: TaskManager,
    timeout_seconds: float = 300.0,
) -> dict:
    """Create a request_input tool bound to a specific A2A task.

    Returns a dict with:
    - name: str — tool name for the LLM
    - description: str — guidance for when to use it
    - handler: async callable(question: str) -> str
    - event: asyncio.Event — for external resolution
    - response_holder: dict — mutable container for the response

    The event and response_holder are exposed so the router can
    resolve the suspension when the client sends a follow-up.
    """
    event = asyncio.Event()
    response_holder: dict[str, str] = {}

    async def request_input_handler(question: str) -> str:
        """Ask the calling agent for clarification.

        Suspends execution until the client responds or timeout.
        """
        # Signal INPUT_REQUIRED on the task
        await task_manager.request_input(task_id, question, event, response_holder)

        # Suspend until client responds
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            msg = f"Client did not respond within {timeout_seconds}s"
            raise TimeoutError(msg) from None

        return response_holder["response"]

    return {
        "name": "request_input",
        "description": (
            "Ask the calling agent or user for clarification or additional "
            "information. Use this when you need more details to complete "
            "the task."
        ),
        "handler": request_input_handler,
        "event": event,
        "response_holder": response_holder,
    }


def resolve_input_request(
    event: asyncio.Event,
    response_holder: dict,
    response: str,
) -> None:
    """Resolve a pending request_input call with the client's response.

    Called by the router when a follow-up message arrives for
    an INPUT_REQUIRED task.
    """
    response_holder["response"] = response
    event.set()
