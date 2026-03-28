"""Unit tests for the request_input tool (INPUT_REQUIRED mechanics).

Tests the asyncio.Event-based suspension pattern that enables
server-initiated turn-taking in A2A:

1. Tool is created → bound to a specific task
2. LLM calls the tool with a question → execution suspends
3. Client sends follow-up → asyncio.Event is resolved
4. Tool returns the client's response to the LLM
5. LLM continues reasoning

Also tests timeout (client doesn't respond) and multiple rounds
(agent asks more than one question).

These are pure async tests — no HTTP, no database, no LLM.
"""

import asyncio

import pytest

from langflow.api.a2a.request_input_tool import (
    create_request_input_tool,
    resolve_input_request,
)
from langflow.api.a2a.task_manager import TaskManager

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_manager():
    return TaskManager()


@pytest.fixture
async def task_with_tool(task_manager):
    """Create a task and its associated request_input tool."""
    task = await task_manager.create_task(flow_id="flow-1", context_id="ctx-1", task_id="task-input-1")
    tool_info = create_request_input_tool(
        task_id=task["id"],
        task_manager=task_manager,
    )
    return task, tool_info


# ---------------------------------------------------------------------------
# Tests: Tool creation
# ---------------------------------------------------------------------------


class TestToolCreation:
    """Tests for creating the request_input tool."""

    async def test_tool_has_correct_name(self, task_with_tool):
        """The tool must be named 'request_input' so LLMs can call it."""
        _task, tool_info = task_with_tool
        assert tool_info["name"] == "request_input"

    async def test_tool_has_description(self, task_with_tool):
        """The tool description guides the LLM on when to use it."""
        _task, tool_info = task_with_tool
        assert "clarification" in tool_info["description"].lower() or "additional" in tool_info["description"].lower()

    async def test_tool_has_handler(self, task_with_tool):
        """The tool provides an async handler function."""
        _task, tool_info = task_with_tool
        assert callable(tool_info["handler"])


# ---------------------------------------------------------------------------
# Tests: Suspension and resolution
# ---------------------------------------------------------------------------


class TestSuspensionAndResolution:
    """Tests for the core asyncio.Event suspension pattern.

    When the LLM calls request_input:
    1. The handler suspends (awaits an asyncio.Event)
    2. The task state transitions to INPUT_REQUIRED
    3. An external call resolves the event with the client's response
    4. The handler returns that response to the LLM
    """

    async def test_handler_suspends_until_resolved(self, task_with_tool):
        """Calling the handler blocks until resolve_input_request is called.

        This simulates the core flow: LLM asks a question, execution
        pauses, client responds, execution resumes.
        """
        task, tool_info = task_with_tool
        handler = tool_info["handler"]

        # Start the handler (it will suspend)
        result_future = asyncio.create_task(handler(question="Which environment?"))

        # Give the handler time to suspend
        await asyncio.sleep(0.05)
        assert not result_future.done(), "Handler should be suspended, not done"

        # Resolve with client's response
        resolve_input_request(tool_info["event"], tool_info["response_holder"], "prod-us")

        # Handler should now complete
        result = await asyncio.wait_for(result_future, timeout=1.0)
        assert result == "prod-us"

    async def test_task_transitions_to_input_required(self, task_with_tool, task_manager):
        """When the handler is called, the task state becomes INPUT_REQUIRED.

        This is what the client sees — the task status tells them
        the agent needs more information.
        """
        task, tool_info = task_with_tool
        handler = tool_info["handler"]
        await task_manager.update_state(task["id"], "working")

        # Start handler (will set INPUT_REQUIRED)
        result_future = asyncio.create_task(handler(question="What region?"))
        await asyncio.sleep(0.05)

        # Check task state
        current = await task_manager.get_task(task["id"])
        assert current["status"]["state"] == "input-required"

        # Clean up
        resolve_input_request(tool_info["event"], tool_info["response_holder"], "us-east-1")
        await asyncio.wait_for(result_future, timeout=1.0)

    async def test_question_is_stored_on_task(self, task_with_tool, task_manager):
        """The question from the LLM is stored on the task status message.

        This is how the client knows WHAT the agent is asking for.
        """
        task, tool_info = task_with_tool
        handler = tool_info["handler"]
        await task_manager.update_state(task["id"], "working")

        result_future = asyncio.create_task(handler(question="Which database?"))
        await asyncio.sleep(0.05)

        current = await task_manager.get_task(task["id"])
        status_msg = current["status"].get("message", {})
        parts = status_msg.get("parts", [])
        assert any("Which database?" in p.get("text", "") for p in parts)

        # Clean up
        resolve_input_request(tool_info["event"], tool_info["response_holder"], "postgres")
        await asyncio.wait_for(result_future, timeout=1.0)

    async def test_resolution_returns_exact_client_response(self, task_with_tool):
        """The handler returns exactly what the client sent — no transformation."""
        task, tool_info = task_with_tool
        handler = tool_info["handler"]

        result_future = asyncio.create_task(handler(question="Pick a color"))
        await asyncio.sleep(0.05)

        resolve_input_request(tool_info["event"], tool_info["response_holder"], "blue")
        result = await asyncio.wait_for(result_future, timeout=1.0)
        assert result == "blue"


# ---------------------------------------------------------------------------
# Tests: Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    """Tests for timeout when the client doesn't respond."""

    async def test_timeout_raises_after_deadline(self, task_manager):
        """If the client doesn't respond within the timeout, the handler
        raises an exception that the LLM receives as a tool error.

        The Agent can then decide to proceed without the info or fail.
        """
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="timeout-task")
        tool_info = create_request_input_tool(
            task_id=task["id"],
            task_manager=task_manager,
            timeout_seconds=0.1,  # Very short timeout for testing
        )
        handler = tool_info["handler"]

        # Call handler — it will timeout since nobody resolves
        with pytest.raises(TimeoutError, match="did not respond"):
            await handler(question="Hello?")


# ---------------------------------------------------------------------------
# Tests: Multiple rounds
# ---------------------------------------------------------------------------


class TestMultipleRounds:
    """Tests for agents that ask multiple questions in one task.

    The agent can call request_input multiple times — each call
    creates a new suspension point with a new asyncio.Event.
    """

    async def test_two_sequential_questions(self, task_manager):
        """The agent asks two questions, each resolved independently.

        Round 1: "Which env?" → "staging"
        Round 2: "Which region?" → "us-west-2"
        """
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="multi-q")

        # Round 1
        tool_info_1 = create_request_input_tool(
            task_id=task["id"],
            task_manager=task_manager,
        )
        handler_1 = tool_info_1["handler"]
        future_1 = asyncio.create_task(handler_1(question="Which env?"))
        await asyncio.sleep(0.05)

        resolve_input_request(tool_info_1["event"], tool_info_1["response_holder"], "staging")
        result_1 = await asyncio.wait_for(future_1, timeout=1.0)
        assert result_1 == "staging"

        # Round 2 — new tool instance (agent creates a new call)
        tool_info_2 = create_request_input_tool(
            task_id=task["id"],
            task_manager=task_manager,
        )
        handler_2 = tool_info_2["handler"]
        future_2 = asyncio.create_task(handler_2(question="Which region?"))
        await asyncio.sleep(0.05)

        resolve_input_request(tool_info_2["event"], tool_info_2["response_holder"], "us-west-2")
        result_2 = await asyncio.wait_for(future_2, timeout=1.0)
        assert result_2 == "us-west-2"
