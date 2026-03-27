"""Integration tests for the A2A message:stream endpoint.

Tests the SSE streaming round-trip:
1. Client POSTs to /a2a/{slug}/v1/message:stream
2. Server returns a StreamingResponse with SSE events
3. Client receives A2A-formatted status and artifact updates

Since we mock simple_run_flow, we simulate the streaming by having
the mock write events to the EventManager queue directly. This tests
the full pipeline from HTTP request to SSE response.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

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


async def _create_a2a_enabled_flow(
    client: AsyncClient, headers: dict, slug: str
) -> dict:
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


def _make_a2a_message(text: str, context_id: str | None = None) -> dict:
    msg = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": "msg-stream-test",
        },
    }
    if context_id:
        msg["message"]["contextId"] = context_id
    return msg


def _mock_run_response(text: str = "Streamed response"):
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


def _parse_sse_events(raw_text: str) -> list[dict]:
    """Parse SSE text into a list of JSON event dicts.

    SSE format:
        data: {"kind": "status-update", ...}\n\n
        data: {"kind": "artifact-update", ...}\n\n
    """
    events = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                continue
    return events


# ---------------------------------------------------------------------------
# Tests: Streaming happy path
# ---------------------------------------------------------------------------


class TestMessageStreamHappyPath:
    """Tests for successful streaming flow execution."""

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_stream_returns_sse_response(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """message:stream returns a streaming response with SSE media type.

        The response should be text/event-stream, not application/json.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="stream-agent")

        response = await client.post(
            "/a2a/stream-agent/v1/message:stream",
            json=_make_a2a_message("Hello"),
            headers=logged_in_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_stream_contains_completed_event(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """The stream must end with a COMPLETED status event.

        This tells the client the task is done and no more events
        will arrive.
        """
        mock_run.return_value = _mock_run_response("Final answer")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="complete-stream")

        response = await client.post(
            "/a2a/complete-stream/v1/message:stream",
            json=_make_a2a_message("Question?"),
            headers=logged_in_headers,
        )

        events = _parse_sse_events(response.text)
        # Should have at least one status-update with completed
        status_events = [e for e in events if e.get("kind") == "status-update"]
        assert any(e["status"]["state"] == "completed" for e in status_events)

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_stream_contains_working_event(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """The stream should include a WORKING status event at the start.

        This tells the client the flow has started executing.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="working-stream")

        response = await client.post(
            "/a2a/working-stream/v1/message:stream",
            json=_make_a2a_message("Go"),
            headers=logged_in_headers,
        )

        events = _parse_sse_events(response.text)
        status_events = [e for e in events if e.get("kind") == "status-update"]
        assert any(e["status"]["state"] == "working" for e in status_events)

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_stream_preserves_task_and_context_ids(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """Every SSE event carries the taskId and contextId.

        This lets clients correlate events with the right task
        even if they have multiple streams open.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="id-stream")

        response = await client.post(
            "/a2a/id-stream/v1/message:stream",
            json=_make_a2a_message("Go", context_id="ctx-stream-1"),
            headers=logged_in_headers,
        )

        events = _parse_sse_events(response.text)
        for event in events:
            assert "taskId" in event
            assert "contextId" in event


# ---------------------------------------------------------------------------
# Tests: Error handling in streaming
# ---------------------------------------------------------------------------


class TestMessageStreamErrors:
    """Tests for error handling during streaming."""

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_stream_error_produces_failed_event(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """When flow execution fails, the stream includes a FAILED event.

        The client should see the error without the connection just dying.
        """
        mock_run.side_effect = Exception("LLM provider down")
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="error-stream")

        response = await client.post(
            "/a2a/error-stream/v1/message:stream",
            json=_make_a2a_message("Fail please"),
            headers=logged_in_headers,
        )

        assert response.status_code == 200  # SSE connection opened
        events = _parse_sse_events(response.text)
        status_events = [e for e in events if e.get("kind") == "status-update"]
        assert any(e["status"]["state"] == "failed" for e in status_events)

    async def test_stream_disabled_flow_returns_404(
        self, client: AsyncClient, logged_in_headers
    ):
        """Streaming to a non-existent slug returns 404."""
        response = await client.post(
            "/a2a/nonexistent/v1/message:stream",
            json=_make_a2a_message("Hello"),
            headers=logged_in_headers,
        )
        assert response.status_code == 404

    async def test_stream_requires_auth(
        self, client: AsyncClient, logged_in_headers
    ):
        """message:stream requires authentication."""
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="auth-stream")

        response = await client.post(
            "/a2a/auth-stream/v1/message:stream",
            json=_make_a2a_message("Hello"),
            headers={"Authorization": "Bearer invalid"},
        )
        assert response.status_code in (401, 403)
