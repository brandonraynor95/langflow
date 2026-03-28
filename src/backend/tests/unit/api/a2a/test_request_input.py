"""Unit tests for the request_input tool (redesigned — no suspension).

Tests the stateless request_input pattern:
1. Tool is created → bound to a specific task
2. LLM calls the tool → returns immediately with a pending marker
3. Task transitions to INPUT_REQUIRED
4. Client sends follow-up → new execution starts with same session

No asyncio.Event, no suspension, no held memory.
"""

import pytest

from langflow.api.a2a.request_input_tool import (
    create_request_input_tool,
    extract_input_required_question,
    is_input_required_response,
)
from langflow.api.a2a.task_manager import TaskManager

pytestmark = pytest.mark.asyncio


@pytest.fixture
def task_manager():
    return TaskManager()


class TestToolCreation:
    """Tests for creating the request_input tool."""

    async def test_tool_has_correct_name(self, task_manager):
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        tool_info = create_request_input_tool(task_id=task["id"], task_manager=task_manager)
        assert tool_info["name"] == "request_input"

    async def test_tool_has_description(self, task_manager):
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        tool_info = create_request_input_tool(task_id=task["id"], task_manager=task_manager)
        assert "clarification" in tool_info["description"].lower() or "information" in tool_info["description"].lower()

    async def test_tool_has_handler(self, task_manager):
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        tool_info = create_request_input_tool(task_id=task["id"], task_manager=task_manager)
        assert callable(tool_info["handler"])


class TestHandlerReturnsImmediately:
    """Tests that the handler returns immediately with a marked response.

    No suspension — the tool returns, the flow completes, and the
    framework detects the marker to transition to input-required.
    """

    async def test_handler_returns_marked_response(self, task_manager):
        """The handler returns a string containing the INPUT_REQUIRED marker."""
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        await task_manager.update_state(task["id"], "working")
        tool_info = create_request_input_tool(task_id=task["id"], task_manager=task_manager)

        result = await tool_info["handler"](question="Which environment?")

        assert is_input_required_response(result)
        assert "Which environment?" in result

    async def test_handler_sets_task_to_input_required(self, task_manager):
        """Calling the handler transitions the task to INPUT_REQUIRED."""
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        await task_manager.update_state(task["id"], "working")
        tool_info = create_request_input_tool(task_id=task["id"], task_manager=task_manager)

        await tool_info["handler"](question="Which region?")

        current = await task_manager.get_task(task["id"])
        assert current["status"]["state"] == "input-required"

    async def test_question_stored_on_task(self, task_manager):
        """The question is stored on the task status message."""
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        await task_manager.update_state(task["id"], "working")
        tool_info = create_request_input_tool(task_id=task["id"], task_manager=task_manager)

        await tool_info["handler"](question="Which database?")

        current = await task_manager.get_task(task["id"])
        parts = current["status"]["message"]["parts"]
        assert any("Which database?" in p["text"] for p in parts)


class TestMarkerDetection:
    """Tests for detecting and extracting the input-required marker."""

    def test_marked_response_detected(self):
        assert is_input_required_response("__a2a_input_required__:Which env?")

    def test_normal_response_not_detected(self):
        assert not is_input_required_response("The capital of France is Paris.")

    def test_none_not_detected(self):
        assert not is_input_required_response(None)

    def test_extract_question(self):
        q = extract_input_required_question("__a2a_input_required__:Which env?")
        assert q == "Which env?"

    def test_extract_from_normal_text(self):
        q = extract_input_required_question("Just some text")
        assert q == "Just some text"
