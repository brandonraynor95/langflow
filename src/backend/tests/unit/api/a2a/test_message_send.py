"""Integration tests for the A2A message:send endpoint.

Tests the full HTTP round-trip:
1. Client sends an A2A message to POST /a2a/{slug}/v1/message:send
2. Langflow executes the flow
3. Client receives an A2A Task response with artifacts

These tests use the real FastAPI app and database, but mock the
flow execution engine (LLM calls) to avoid external dependencies.

Test organization:
- TestMessageSendHappyPath: successful flow execution
- TestMessageSendAuth: authentication enforcement
- TestMessageSendErrors: error handling paths
- TestTaskEndpoints: task polling and cancellation
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from langflow.services.database.models.flow.model import FlowCreate

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_flow_data() -> dict:
    """Create minimal flow graph data that passes A2A eligibility."""
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


async def _create_a2a_enabled_flow(
    client: AsyncClient,
    headers: dict,
    slug: str = "test-agent",
    name: str = "Test Agent",
) -> dict:
    """Create a flow and enable A2A on it. Returns the flow JSON."""
    flow = FlowCreate(name=name, description="Test", data=_make_agent_flow_data())
    response = await client.post("api/v1/flows/", json=flow.model_dump(), headers=headers)
    assert response.status_code == 201
    flow_json = response.json()

    config_response = await client.put(
        f"api/v1/flows/{flow_json['id']}/a2a-config",
        json={"a2a_enabled": True, "a2a_agent_slug": slug},
        headers=headers,
    )
    assert config_response.status_code == 200
    return flow_json


def _make_a2a_message(text: str, context_id: str | None = None) -> dict:
    """Create an A2A message payload for message:send."""
    msg = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": "msg-001",
        },
    }
    if context_id:
        msg["message"]["contextId"] = context_id
    return msg


def _mock_run_response(text: str = "Mocked agent response"):
    """Create a mock RunResponse matching simple_run_flow's return type."""
    from unittest.mock import MagicMock

    run_output = MagicMock()
    run_output.inputs = {}
    result_data = MagicMock()
    result_data.results = {"message": {"text": text}}
    result_data.messages = [MagicMock(message=text)]
    run_output.outputs = [result_data]

    response = MagicMock()
    response.outputs = [run_output]
    response.session_id = "a2a-test-session"
    return response


# ---------------------------------------------------------------------------
# Tests: Happy path
# ---------------------------------------------------------------------------


class TestMessageSendHappyPath:
    """Tests for successful flow execution via message:send.

    These tests mock the flow execution engine to avoid needing
    real LLM credentials, while testing the full HTTP round-trip
    and A2A response formatting.
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_send_text_message_returns_completed_task(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """Sending a text message executes the flow and returns a COMPLETED task.

        This is the core happy path:
        1. Client sends POST /message:send with a text message
        2. Flow executes
        3. Response contains a Task with state=completed and artifacts
        """
        mock_run.return_value = _mock_run_response("Hello from the agent!")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="happy-agent")

        payload = _make_a2a_message("What is the meaning of life?")
        response = await client.post(
            "/a2a/happy-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )

        assert response.status_code == 200
        body = response.json()

        # Response should be a Task object
        assert body["status"]["state"] == "completed"
        assert body["id"] is not None

        # Task should contain artifacts with the flow's output
        assert len(body["artifacts"]) > 0
        first_artifact = body["artifacts"][0]
        assert first_artifact["parts"][0]["kind"] == "text"
        assert "Hello from the agent!" in first_artifact["parts"][0]["text"]

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_task_has_context_id(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """The returned task preserves the contextId from the request.

        This is essential for multi-turn conversations — the client
        uses contextId to continue the conversation in Turn 2.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="context-agent")

        payload = _make_a2a_message("Hello", context_id="ctx-my-conversation")
        response = await client.post(
            "/a2a/context-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["contextId"] == "ctx-my-conversation"

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_idempotent_retry_returns_cached_result(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """Sending the same taskId twice returns the cached result.

        The flow should NOT execute a second time. This prevents
        duplicate work when a client retries after a timeout.
        """
        mock_run.return_value = _mock_run_response("Original result")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="retry-agent")

        payload = _make_a2a_message("Do expensive work")
        payload["taskId"] = "idempotent-task-123"

        # First call — executes the flow
        response1 = await client.post(
            "/a2a/retry-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )
        assert response1.status_code == 200
        assert mock_run.call_count == 1

        # Second call with same taskId — returns cached result
        response2 = await client.post(
            "/a2a/retry-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )
        assert response2.status_code == 200
        # Flow should NOT have been called a second time
        assert mock_run.call_count == 1
        assert response2.json()["status"]["state"] == "completed"


# ---------------------------------------------------------------------------
# Tests: Authentication
# ---------------------------------------------------------------------------


class TestMessageSendAuth:
    """Tests for authentication on the message:send endpoint."""

    async def test_unauthenticated_request_rejected(
        self, client: AsyncClient, logged_in_headers
    ):
        """message:send requires authentication.

        Unlike the public AgentCard, message:send handles actual
        flow execution and must be protected.
        """
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="auth-agent")

        payload = _make_a2a_message("Hello")
        response = await client.post(
            "/a2a/auth-agent/v1/message:send",
            json=payload,
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestMessageSendErrors:
    """Tests for error handling in message:send."""

    async def test_disabled_flow_returns_404(
        self, client: AsyncClient, logged_in_headers
    ):
        """Sending to a slug that exists but has A2A disabled returns 404."""
        # Create flow but don't enable A2A
        flow = FlowCreate(name="Disabled", data=_make_agent_flow_data())
        await client.post("api/v1/flows/", json=flow.model_dump(), headers=logged_in_headers)

        payload = _make_a2a_message("Hello")
        response = await client.post(
            "/a2a/nonexistent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )
        assert response.status_code == 404

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_flow_execution_error_returns_failed_task(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """When the flow execution raises an exception, the task becomes FAILED.

        The error message is included in the task status so the caller
        can understand what went wrong.
        """
        mock_run.side_effect = Exception("LLM provider rate limited")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="error-agent")

        payload = _make_a2a_message("Do something")
        response = await client.post(
            "/a2a/error-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )

        assert response.status_code == 200  # A2A returns 200 with failed task state
        body = response.json()
        assert body["status"]["state"] == "failed"


# ---------------------------------------------------------------------------
# Tests: Task endpoints
# ---------------------------------------------------------------------------


class TestTaskEndpoints:
    """Tests for task polling and cancellation endpoints."""

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_get_task_returns_current_state(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """GET /tasks/{task_id} returns the current task state.

        This is the polling endpoint for clients that lost their
        SSE connection or don't support streaming.
        """
        mock_run.return_value = _mock_run_response("Done")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="poll-agent")

        # Send a message to create a task
        payload = _make_a2a_message("Work please")
        send_response = await client.post(
            "/a2a/poll-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )
        task_id = send_response.json()["id"]

        # Poll the task
        get_response = await client.get(
            f"/a2a/poll-agent/v1/tasks/{task_id}",
            headers=logged_in_headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == task_id
        assert get_response.json()["status"]["state"] == "completed"

    async def test_get_nonexistent_task_returns_404(
        self, client: AsyncClient, logged_in_headers
    ):
        """Polling a task that doesn't exist returns 404."""
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="poll-agent-2")

        response = await client.get(
            "/a2a/poll-agent-2/v1/tasks/nonexistent-task-id",
            headers=logged_in_headers,
        )
        assert response.status_code == 404

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_cancel_task(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """POST /tasks/{task_id}:cancel sets the task to CANCELED.

        Cancellation is best-effort — the flow may have already completed.
        """
        mock_run.return_value = _mock_run_response("Done")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="cancel-agent")

        # Create a task
        payload = _make_a2a_message("Work")
        send_response = await client.post(
            "/a2a/cancel-agent/v1/message:send",
            json=payload,
            headers=logged_in_headers,
        )
        task_id = send_response.json()["id"]

        # Cancel it
        cancel_response = await client.post(
            f"/a2a/cancel-agent/v1/tasks/{task_id}:cancel",
            headers=logged_in_headers,
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"]["state"] == "canceled"

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_list_tasks_by_context(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """GET /tasks?contextId=... returns tasks for that conversation."""
        mock_run.return_value = _mock_run_response("Response")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="list-agent")

        # Send two messages in same context
        for text in ["Turn 1", "Turn 2"]:
            await client.post(
                "/a2a/list-agent/v1/message:send",
                json=_make_a2a_message(text, context_id="conversation-1"),
                headers=logged_in_headers,
            )

        # List tasks for that context
        response = await client.get(
            "/a2a/list-agent/v1/tasks?contextId=conversation-1",
            headers=logged_in_headers,
        )
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 2
