"""Integration tests for the INPUT_REQUIRED flow via HTTP endpoints.

Tests the redesigned stateless pattern:
1. Client sends message:send → flow executes
2. If the agent called request_input, the task is INPUT_REQUIRED
3. Client sends follow-up message:send → new execution with same session
4. Flow completes → COMPLETED

No asyncio.Event, no suspension. The follow-up triggers a fresh
flow execution with the same contextId (same session/history).
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from langflow.services.database.models.flow.model import FlowCreate

pytestmark = pytest.mark.asyncio


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


class TestInputRequiredStateless:
    """Tests the stateless INPUT_REQUIRED pattern.

    When the task_manager is marked as input-required (by the request_input
    tool during execution), the router returns the task in that state.
    The client then sends a follow-up which starts a new execution.
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_input_required_task_returned_when_marked(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """When the flow sets input-required on the task during execution,
        the response has state=input-required instead of completed.
        """
        from langflow.api.a2a.router import _task_manager

        # Mock that sets input-required during execution (simulating
        # the request_input tool being called by the LLM)
        async def mock_with_input_required(*, flow=None, input_request=None, **kwargs):
            tasks = await _task_manager.list_tasks()
            if tasks:
                await _task_manager.set_input_required(tasks[-1]["id"], "Which env?")
            return _mock_run_response("__a2a_input_required__:Which env?")

        mock_run.side_effect = mock_with_input_required
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="ir-stateless")

        response = await client.post(
            "/a2a/ir-stateless/v1/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Deploy my app"}],
                    "contextId": "ctx-ir",
                },
            },
            headers=logged_in_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"]["state"] == "input-required"

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_follow_up_starts_new_execution(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """When the client sends a follow-up to an input-required task,
        a new execution starts (not a resume of the old one).
        """
        from langflow.api.a2a.router import _task_manager

        call_count = 0

        async def mock_execution(*, flow=None, input_request=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: mark input-required
                tasks = await _task_manager.list_tasks()
                if tasks:
                    await _task_manager.set_input_required(tasks[-1]["id"], "Which env?")
                return _mock_run_response("__a2a_input_required__:Which env?")
            # Second call: complete normally
            return _mock_run_response("Deployed to prod-us")

        mock_run.side_effect = mock_execution
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="ir-followup")

        # First message → input-required
        r1 = await client.post(
            "/a2a/ir-followup/v1/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Deploy my app"}],
                    "contextId": "ctx-followup",
                },
            },
            headers=logged_in_headers,
        )
        assert r1.json()["status"]["state"] == "input-required"
        task_id = r1.json()["id"]

        # Follow-up → new execution → completed
        r2 = await client.post(
            "/a2a/ir-followup/v1/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "prod-us"}],
                    "contextId": "ctx-followup",
                },
                "taskId": task_id,
            },
            headers=logged_in_headers,
        )
        assert r2.json()["status"]["state"] == "completed"
        # Two separate flow executions happened
        assert call_count == 2

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_poll_shows_input_required_with_question(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """GET /tasks/{id} shows input-required state with the agent's question."""
        from langflow.api.a2a.router import _task_manager

        async def mock_with_ir(*, flow=None, input_request=None, **kwargs):
            tasks = await _task_manager.list_tasks()
            if tasks:
                await _task_manager.set_input_required(tasks[-1]["id"], "What database?")
            return _mock_run_response("__a2a_input_required__:What database?")

        mock_run.side_effect = mock_with_ir
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="ir-poll")

        r = await client.post(
            "/a2a/ir-poll/v1/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Set up DB"}],
                    "contextId": "ctx-poll",
                },
            },
            headers=logged_in_headers,
        )
        task_id = r.json()["id"]

        poll = await client.get(
            f"/a2a/ir-poll/v1/tasks/{task_id}",
            headers=logged_in_headers,
        )
        assert poll.json()["status"]["state"] == "input-required"
        assert "database" in poll.json()["status"]["message"]["parts"][0]["text"].lower()
