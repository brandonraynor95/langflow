"""Integration tests for the INPUT_REQUIRED flow via HTTP endpoints.

Tests the end-to-end flow:
1. Client sends message:send → flow starts executing
2. Agent calls request_input → task transitions to INPUT_REQUIRED
3. Client sends follow-up message:send with same taskId
4. Agent receives client's response and continues → COMPLETED

Since we mock simple_run_flow, we simulate INPUT_REQUIRED by having
the mock interact with the task manager directly.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from langflow.api.a2a.request_input_tool import create_request_input_tool, resolve_input_request
from langflow.services.database.models.flow.model import FlowCreate

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_flow_data() -> dict:
    return {
        "nodes": [
            {"id": "chatinput-1", "data": {"type": "ChatInput", "node": {"template": {}}}},
            {"id": "agent-1", "data": {"type": "Agent", "node": {"template": {}}}},
            {"id": "chatoutput-1", "data": {"type": "ChatOutput", "node": {"template": {}}}},
        ],
        "edges": [
            {"source": "chatinput-1", "target": "agent-1"},
            {"source": "agent-1", "target": "chatoutput-1"},
        ],
    }


async def _create_a2a_enabled_flow(client: AsyncClient, headers: dict, slug: str) -> dict:
    flow = FlowCreate(name=f"Flow {slug}", description="Test", data=_make_agent_flow_data())
    response = await client.post("api/v1/flows/", json=flow.model_dump(), headers=headers)
    assert response.status_code == 201
    flow_json = response.json()
    config = await client.put(
        f"api/v1/flows/{flow_json['id']}/a2a-config",
        json={"a2a_enabled": True, "a2a_agent_slug": slug},
        headers=headers,
    )
    assert config.status_code == 200
    return flow_json


def _make_a2a_message(text: str, context_id: str | None = None, task_id: str | None = None) -> dict:
    msg = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": "msg-ir-test",
        },
    }
    if context_id:
        msg["message"]["contextId"] = context_id
    if task_id:
        msg["taskId"] = task_id
    return msg


def _mock_run_response(text: str = "Final answer"):
    from unittest.mock import MagicMock
    run_output = MagicMock()
    run_output.inputs = {}
    result_data = MagicMock()
    result_data.results = {"message": {"text": text}}
    result_data.messages = [MagicMock(message=text)]
    run_output.outputs = [result_data]
    response = MagicMock()
    response.outputs = [run_output]
    response.session_id = "mock-session"
    return response


# ---------------------------------------------------------------------------
# Tests: Follow-up message resolves INPUT_REQUIRED
# ---------------------------------------------------------------------------


class TestInputRequiredFollowUp:
    """Tests that a follow-up message to an INPUT_REQUIRED task resolves it.

    This is the core INPUT_REQUIRED flow:
    1. Initial request creates a task and starts execution
    2. Execution suspends (agent needs clarification)
    3. Task is marked INPUT_REQUIRED with the question
    4. Client sends follow-up with same taskId
    5. Execution resumes with client's answer
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_follow_up_to_input_required_task(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """Send initial message, simulate INPUT_REQUIRED, send follow-up,
        verify the task completes.

        We simulate INPUT_REQUIRED by:
        1. Having the initial mock hang (simulating suspended execution)
        2. Manually setting the task to INPUT_REQUIRED via task manager
        3. Sending the follow-up message
        4. Verifying the follow-up is acknowledged
        """
        from langflow.api.a2a.router import _task_manager

        await _create_a2a_enabled_flow(client, logged_in_headers, slug="ir-agent")

        # Make the first call create a task that we'll manually set to INPUT_REQUIRED
        mock_run.return_value = _mock_run_response("After clarification")

        # First call — creates the task normally
        response1 = await client.post(
            "/a2a/ir-agent/v1/message:send",
            json=_make_a2a_message("Deploy something", context_id="ctx-ir"),
            headers=logged_in_headers,
        )
        assert response1.status_code == 200
        task_id = response1.json()["id"]

        # Manually set task to INPUT_REQUIRED (simulating agent suspension)
        await _task_manager.update_state(task_id, "input-required")
        _task_manager._tasks[task_id]["status"]["message"] = {
            "role": "agent",
            "parts": [{"kind": "text", "text": "Which environment?"}],
        }
        # Register a pending input request
        _task_manager._pending_inputs[task_id] = {
            "event": asyncio.Event(),
            "response_holder": {},
        }

        # Send follow-up with same taskId
        response2 = await client.post(
            "/a2a/ir-agent/v1/message:send",
            json=_make_a2a_message("prod-us", task_id=task_id),
            headers=logged_in_headers,
        )

        assert response2.status_code == 200
        body = response2.json()
        # The follow-up should acknowledge the input was received
        assert body["id"] == task_id

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_get_input_required_task_shows_question(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """Polling an INPUT_REQUIRED task shows the agent's question.

        The client uses GET /tasks/{id} to see what the agent is asking.
        """
        from langflow.api.a2a.router import _task_manager

        await _create_a2a_enabled_flow(client, logged_in_headers, slug="poll-ir-agent")
        mock_run.return_value = _mock_run_response()

        # Create a task
        response = await client.post(
            "/a2a/poll-ir-agent/v1/message:send",
            json=_make_a2a_message("Do work"),
            headers=logged_in_headers,
        )
        task_id = response.json()["id"]

        # Manually set to INPUT_REQUIRED with a question
        await _task_manager.update_state(task_id, "input-required")
        _task_manager._tasks[task_id]["status"]["message"] = {
            "role": "agent",
            "parts": [{"kind": "text", "text": "Which database should I use?"}],
        }

        # Poll the task
        poll_response = await client.get(
            f"/a2a/poll-ir-agent/v1/tasks/{task_id}",
            headers=logged_in_headers,
        )
        assert poll_response.status_code == 200
        task = poll_response.json()
        assert task["status"]["state"] == "input-required"
        assert "Which database" in task["status"]["message"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Tests: request_input tool with task manager integration
# ---------------------------------------------------------------------------


class TestRequestInputTaskManagerIntegration:
    """Tests that request_input tool correctly interacts with TaskManager."""

    async def test_tool_sets_pending_input_on_task_manager(self):
        """Creating a tool and calling it registers a pending input request
        on the task manager, so the router knows to route follow-ups.
        """
        from langflow.api.a2a.task_manager import TaskManager

        tm = TaskManager()
        task = await tm.create_task(flow_id="f", context_id="c", task_id="pending-test")
        await tm.update_state(task["id"], "working")

        tool_info = create_request_input_tool(
            task_id=task["id"], task_manager=tm,
        )

        # Start the handler (will suspend and register pending input)
        handler = tool_info["handler"]
        future = asyncio.create_task(handler(question="What color?"))
        await asyncio.sleep(0.05)

        # Check that the task manager has a pending input
        assert task["id"] in tm._pending_inputs

        # Clean up
        resolve_input_request(tool_info["event"], tool_info["response_holder"], "red")
        await asyncio.wait_for(future, timeout=1.0)

    async def test_resolve_clears_pending_input(self):
        """After resolution, the pending input is cleared from task manager."""
        from langflow.api.a2a.task_manager import TaskManager

        tm = TaskManager()
        task = await tm.create_task(flow_id="f", context_id="c", task_id="clear-test")
        await tm.update_state(task["id"], "working")

        tool_info = create_request_input_tool(
            task_id=task["id"], task_manager=tm,
        )
        handler = tool_info["handler"]
        future = asyncio.create_task(handler(question="Pick one"))
        await asyncio.sleep(0.05)

        assert "clear-test" in tm._pending_inputs

        # Resolve via task manager's resolve method
        await tm.resolve_input("clear-test", "option-a")
        result = await asyncio.wait_for(future, timeout=1.0)

        assert result == "option-a"
        assert "clear-test" not in tm._pending_inputs
