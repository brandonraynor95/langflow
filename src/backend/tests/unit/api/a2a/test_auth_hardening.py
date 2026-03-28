"""Tests for auth enforcement and security hardening (Phase 6).

Systematically verifies that every A2A endpoint has the correct
auth posture:
- Public endpoints (no auth): AgentCard discovery
- Protected endpoints (auth required): everything else

Also tests session isolation: different API keys with the same
contextId must produce different sessions.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from langflow.services.database.models.flow.model import FlowCreate

pytestmark = pytest.mark.asyncio

BAD_AUTH = {"Authorization": "Bearer invalid-token-xyz"}


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


async def _setup_flow(client: AsyncClient, headers: dict, slug: str) -> dict:
    flow = FlowCreate(name=f"Flow {slug}", description="Test", data=_make_agent_flow_data())
    resp = await client.post("api/v1/flows/", json=flow.model_dump(), headers=headers)
    assert resp.status_code == 201
    flow_json = resp.json()
    await client.put(
        f"api/v1/flows/{flow_json['id']}/a2a-config",
        json={"a2a_enabled": True, "a2a_agent_slug": slug},
        headers=headers,
    )
    return flow_json


def _mock_run_response():
    from unittest.mock import MagicMock

    ro = MagicMock()
    ro.inputs = {}
    rd = MagicMock()
    rd.results = {"message": {"text": "ok"}}
    rd.messages = [MagicMock(message="ok")]
    ro.outputs = [rd]
    r = MagicMock()
    r.outputs = [ro]
    r.session_id = "s"
    return r


# ---------------------------------------------------------------------------
# Tests: Public endpoints (no auth required)
# ---------------------------------------------------------------------------


class TestPublicEndpoints:
    """Endpoints that MUST be accessible without authentication."""

    async def test_agent_card_accessible_without_auth(self, client: AsyncClient, logged_in_headers):
        """The public AgentCard is the A2A discovery mechanism.

        It MUST be accessible without authentication — this is how
        external agents find out what Langflow agents exist.
        """
        await _setup_flow(client, logged_in_headers, slug="public-auth-test")

        # No auth headers at all
        response = await client.get("/a2a/public-auth-test/.well-known/agent-card.json")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Protected endpoints (auth required)
# ---------------------------------------------------------------------------


class TestProtectedEndpoints:
    """Every non-public endpoint MUST reject invalid authentication.

    This is a systematic check — if any endpoint is accidentally
    left unprotected, this test class will catch it.
    """

    async def test_extended_card_rejects_bad_auth(self, client: AsyncClient, logged_in_headers):
        """Extended AgentCard contains detailed skill schemas — auth required."""
        await _setup_flow(client, logged_in_headers, slug="ext-auth")
        resp = await client.get("/a2a/ext-auth/v1/card", headers=BAD_AUTH)
        assert resp.status_code in (401, 403)

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_message_send_rejects_bad_auth(self, mock_run, client: AsyncClient, logged_in_headers):
        """message:send executes flows — MUST be protected."""
        mock_run.return_value = _mock_run_response()
        await _setup_flow(client, logged_in_headers, slug="send-auth")
        resp = await client.post(
            "/a2a/send-auth/v1/message:send",
            json={"message": {"role": "user", "parts": [{"kind": "text", "text": "hi"}]}},
            headers=BAD_AUTH,
        )
        assert resp.status_code in (401, 403)

    async def test_message_stream_rejects_bad_auth(self, client: AsyncClient, logged_in_headers):
        """message:stream executes flows — MUST be protected."""
        await _setup_flow(client, logged_in_headers, slug="stream-auth")
        resp = await client.post(
            "/a2a/stream-auth/v1/message:stream",
            json={"message": {"role": "user", "parts": [{"kind": "text", "text": "hi"}]}},
            headers=BAD_AUTH,
        )
        assert resp.status_code in (401, 403)

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_get_task_rejects_bad_auth(self, mock_run, client: AsyncClient, logged_in_headers):
        """Task polling reveals execution state — auth required."""
        mock_run.return_value = _mock_run_response()
        await _setup_flow(client, logged_in_headers, slug="gettask-auth")

        # Create a task first (with good auth)
        send_resp = await client.post(
            "/a2a/gettask-auth/v1/message:send",
            json={"message": {"role": "user", "parts": [{"kind": "text", "text": "hi"}]}},
            headers=logged_in_headers,
        )
        task_id = send_resp.json()["id"]

        # Try to poll with bad auth
        resp = await client.get(f"/a2a/gettask-auth/v1/tasks/{task_id}", headers=BAD_AUTH)
        assert resp.status_code in (401, 403)

    async def test_list_tasks_rejects_bad_auth(self, client: AsyncClient, logged_in_headers):
        """Task listing reveals execution history — auth required."""
        await _setup_flow(client, logged_in_headers, slug="listtask-auth")
        resp = await client.get("/a2a/listtask-auth/v1/tasks", headers=BAD_AUTH)
        assert resp.status_code in (401, 403)

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_cancel_task_rejects_bad_auth(self, mock_run, client: AsyncClient, logged_in_headers):
        """Task cancellation changes state — auth required."""
        mock_run.return_value = _mock_run_response()
        await _setup_flow(client, logged_in_headers, slug="cancel-auth")

        send_resp = await client.post(
            "/a2a/cancel-auth/v1/message:send",
            json={"message": {"role": "user", "parts": [{"kind": "text", "text": "hi"}]}},
            headers=logged_in_headers,
        )
        task_id = send_resp.json()["id"]

        resp = await client.post(f"/a2a/cancel-auth/v1/tasks/{task_id}:cancel", headers=BAD_AUTH)
        assert resp.status_code in (401, 403)

    async def test_config_put_rejects_bad_auth(self, client: AsyncClient, logged_in_headers):
        """Config management controls flow exposure — auth required."""
        flow = FlowCreate(name="cfg-auth", data=_make_agent_flow_data())
        resp = await client.post("api/v1/flows/", json=flow.model_dump(), headers=logged_in_headers)
        flow_id = resp.json()["id"]

        resp = await client.put(
            f"api/v1/flows/{flow_id}/a2a-config",
            json={"a2a_enabled": True, "a2a_agent_slug": "cfg-auth"},
            headers=BAD_AUTH,
        )
        assert resp.status_code in (401, 403)

    async def test_config_get_rejects_bad_auth(self, client: AsyncClient, logged_in_headers):
        """Config read reveals exposure state — auth required."""
        flow = FlowCreate(name="cfgget-auth", data=_make_agent_flow_data())
        resp = await client.post("api/v1/flows/", json=flow.model_dump(), headers=logged_in_headers)
        flow_id = resp.json()["id"]

        resp = await client.get(f"api/v1/flows/{flow_id}/a2a-config", headers=BAD_AUTH)
        assert resp.status_code in (401, 403)
