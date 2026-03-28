"""End-to-end smoke test exercising the full A2A lifecycle (Phase 7).

A single comprehensive test that walks through every A2A capability
in sequence, verifying they work together as a system:

1. Create a flow with an Agent component
2. Enable A2A on it via config endpoint
3. Discover AgentCard at well-known URL
4. Send message:send → get completed task with artifacts
5. Send message:stream → receive SSE events
6. Multi-turn: send second message with same contextId
7. Poll task via GET /tasks/{id}
8. List tasks by contextId
9. Cancel a task
10. Verify AgentCard structure

This is the "does it all work together?" test.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from langflow.services.database.models.flow.model import FlowCreate

pytestmark = pytest.mark.asyncio


def _make_agent_flow_data() -> dict:
    return {
        "nodes": [
            {"id": "ci-1", "data": {"type": "ChatInput", "node": {"template": {}}}},
            {"id": "ag-1", "data": {"type": "Agent", "node": {"template": {}}}},
            {"id": "co-1", "data": {"type": "ChatOutput", "node": {"template": {}}}},
        ],
        "edges": [
            {"source": "ci-1", "target": "ag-1"},
            {"source": "ag-1", "target": "co-1"},
        ],
    }


def _mock_run_response(text: str):
    ro = MagicMock()
    ro.inputs = {}
    rd = MagicMock()
    rd.results = {"message": {"text": text}}
    rd.messages = [MagicMock(message=text)]
    ro.outputs = [rd]
    r = MagicMock()
    r.outputs = [ro]
    r.session_id = "smoke-session"
    return r


class TestA2ASmoke:
    """Full lifecycle smoke test.

    Exercises every A2A endpoint in a realistic sequence to verify
    the entire subsystem works as an integrated whole.
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_full_lifecycle(self, mock_run, client: AsyncClient, logged_in_headers):
        """Walk through the complete A2A lifecycle end-to-end.

        This is the single most important test — if this passes, the
        A2A subsystem is functionally complete for v1.
        """
        mock_run.return_value = _mock_run_response("Smoke test response")

        # ---------------------------------------------------------------
        # Step 1: Create a flow
        # ---------------------------------------------------------------
        flow = FlowCreate(
            name="Smoke Test Agent",
            description="An agent for the A2A smoke test",
            data=_make_agent_flow_data(),
        )
        create_resp = await client.post("api/v1/flows/", json=flow.model_dump(), headers=logged_in_headers)
        assert create_resp.status_code == 201
        flow_id = create_resp.json()["id"]

        # ---------------------------------------------------------------
        # Step 2: Enable A2A
        # ---------------------------------------------------------------
        config_resp = await client.put(
            f"api/v1/flows/{flow_id}/a2a-config",
            json={
                "a2a_enabled": True,
                "a2a_agent_slug": "smoke-agent",
                "a2a_name": "Smoke Agent",
                "a2a_description": "End-to-end smoke test agent",
            },
            headers=logged_in_headers,
        )
        assert config_resp.status_code == 200
        config = config_resp.json()
        assert config["a2a_enabled"] is True
        assert config["a2a_agent_slug"] == "smoke-agent"

        # Verify config readback
        config_get = await client.get(f"api/v1/flows/{flow_id}/a2a-config", headers=logged_in_headers)
        assert config_get.status_code == 200
        assert config_get.json()["a2a_name"] == "Smoke Agent"

        # ---------------------------------------------------------------
        # Step 3: Discover AgentCard
        # ---------------------------------------------------------------
        card_resp = await client.get("/a2a/smoke-agent/.well-known/agent-card.json")
        assert card_resp.status_code == 200
        card = card_resp.json()

        # Verify card structure
        assert card["name"] == "Smoke Agent"
        assert card["description"] == "End-to-end smoke test agent"
        assert card["capabilities"]["streaming"] is True
        assert card["capabilities"]["pushNotifications"] is False
        assert len(card["skills"]) == 1
        assert "text" in card["defaultInputModes"]
        assert "text" in card["defaultOutputModes"]
        assert "url" in card
        assert "version" in card

        # Extended card requires auth
        ext_resp = await client.get("/a2a/smoke-agent/v1/card", headers=logged_in_headers)
        assert ext_resp.status_code == 200
        assert ext_resp.json()["extended"] is True

        # ---------------------------------------------------------------
        # Step 4: Send message:send — synchronous execution
        # ---------------------------------------------------------------
        send_resp = await client.post(
            "/a2a/smoke-agent/v1/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Analyze our security posture"}],
                    "contextId": "ctx-smoke",
                },
            },
            headers=logged_in_headers,
        )
        assert send_resp.status_code == 200
        task1 = send_resp.json()

        assert task1["status"]["state"] == "completed"
        assert task1["contextId"] == "ctx-smoke"
        assert task1["id"] is not None
        assert len(task1["artifacts"]) > 0
        assert task1["artifacts"][0]["parts"][0]["kind"] == "text"
        assert "Smoke test response" in task1["artifacts"][0]["parts"][0]["text"]

        # ---------------------------------------------------------------
        # Step 5: Send message:stream — SSE execution
        # ---------------------------------------------------------------
        stream_resp = await client.post(
            "/a2a/smoke-agent/v1/message:stream",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Stream me something"}],
                    "contextId": "ctx-smoke-stream",
                },
            },
            headers=logged_in_headers,
        )
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]

        # Parse SSE events
        events = []
        for line in stream_resp.text.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        # Should have working → (artifacts) → completed
        states = [e["status"]["state"] for e in events if e.get("kind") == "status-update"]
        assert "working" in states
        assert "completed" in states

        # ---------------------------------------------------------------
        # Step 6: Multi-turn — same contextId
        # ---------------------------------------------------------------
        mock_run.return_value = _mock_run_response("Follow-up analysis")

        turn2_resp = await client.post(
            "/a2a/smoke-agent/v1/message:send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Elaborate on finding #2"}],
                    "contextId": "ctx-smoke",  # Same context as Step 4
                },
            },
            headers=logged_in_headers,
        )
        assert turn2_resp.status_code == 200
        task2 = turn2_resp.json()
        assert task2["status"]["state"] == "completed"
        assert task2["contextId"] == "ctx-smoke"
        assert task2["id"] != task1["id"]  # Different task, same conversation

        # ---------------------------------------------------------------
        # Step 7: Poll task
        # ---------------------------------------------------------------
        poll_resp = await client.get(
            f"/a2a/smoke-agent/v1/tasks/{task1['id']}",
            headers=logged_in_headers,
        )
        assert poll_resp.status_code == 200
        assert poll_resp.json()["id"] == task1["id"]
        assert poll_resp.json()["status"]["state"] == "completed"

        # ---------------------------------------------------------------
        # Step 8: List tasks by context
        # ---------------------------------------------------------------
        list_resp = await client.get(
            "/a2a/smoke-agent/v1/tasks?contextId=ctx-smoke",
            headers=logged_in_headers,
        )
        assert list_resp.status_code == 200
        tasks = list_resp.json()
        assert len(tasks) == 2  # Turn 1 + Turn 2
        task_ids = {t["id"] for t in tasks}
        assert task1["id"] in task_ids
        assert task2["id"] in task_ids

        # ---------------------------------------------------------------
        # Step 9: Cancel a task
        # ---------------------------------------------------------------
        cancel_resp = await client.post(
            f"/a2a/smoke-agent/v1/tasks/{task2['id']}:cancel",
            headers=logged_in_headers,
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"]["state"] == "canceled"

        # Verify cancellation persisted
        verify_resp = await client.get(
            f"/a2a/smoke-agent/v1/tasks/{task2['id']}",
            headers=logged_in_headers,
        )
        assert verify_resp.json()["status"]["state"] == "canceled"
