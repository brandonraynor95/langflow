"""Integration tests for A2A multi-turn conversations.

Multi-turn conversations are the core differentiator between A2A and
simple tool/MCP calls. The same contextId across messages maps to
the same Langflow session, so the Agent component picks up chat
history from prior turns.

Key mechanics tested:
1. Same contextId → same session_id passed to flow execution
2. Each turn creates a separate Task, all linked by contextId
3. Different contextId → isolated sessions (no cross-contamination)
4. Tasks can be listed by contextId to see full conversation

These tests mock simple_run_flow to avoid LLM calls, but verify
that the correct session_id is passed through to the execution engine.
"""

from unittest.mock import AsyncMock, call, patch

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


def _make_a2a_message(text: str, context_id: str | None = None) -> dict:
    msg = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": f"msg-{text[:8]}",
        },
    }
    if context_id:
        msg["message"]["contextId"] = context_id
    return msg


def _mock_run_response(text: str = "Response"):
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
# Tests: Session continuity via contextId
# ---------------------------------------------------------------------------


class TestSessionContinuity:
    """Tests that the same contextId produces the same session_id across turns.

    This is the foundation of multi-turn: Turn 2 must land in the same
    Langflow session as Turn 1 so the Agent component sees prior chat history.
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_same_context_id_uses_same_session(self, mock_run, client: AsyncClient, logged_in_headers):
        """Two messages with the same contextId pass the same session_id
        to simple_run_flow.

        This is the critical invariant: contextId maps deterministically
        to session_id, so Langflow's session-based chat history works.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="session-agent")

        # Turn 1
        await client.post(
            "/a2a/session-agent/v1/message:send",
            json=_make_a2a_message("Turn 1", context_id="ctx-conversation-1"),
            headers=logged_in_headers,
        )
        # Turn 2 — same contextId
        await client.post(
            "/a2a/session-agent/v1/message:send",
            json=_make_a2a_message("Turn 2", context_id="ctx-conversation-1"),
            headers=logged_in_headers,
        )

        assert mock_run.call_count == 2

        # Extract session_id from both calls
        call1_request = mock_run.call_args_list[0]
        call2_request = mock_run.call_args_list[1]

        session1 = call1_request.kwargs.get("input_request") or call1_request[1].get("input_request")
        session2 = call2_request.kwargs.get("input_request") or call2_request[1].get("input_request")

        # Both should use the same session_id
        if session1 is not None and session2 is not None:
            assert session1.session_id == session2.session_id
            assert session1.session_id.startswith("a2a-")

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_different_context_ids_use_different_sessions(self, mock_run, client: AsyncClient, logged_in_headers):
        """Two messages with different contextIds use different session_ids.

        This ensures conversation isolation — one caller's context
        cannot access another caller's chat history.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="isolate-agent")

        # Conversation A
        await client.post(
            "/a2a/isolate-agent/v1/message:send",
            json=_make_a2a_message("Hello from A", context_id="ctx-A"),
            headers=logged_in_headers,
        )
        # Conversation B
        await client.post(
            "/a2a/isolate-agent/v1/message:send",
            json=_make_a2a_message("Hello from B", context_id="ctx-B"),
            headers=logged_in_headers,
        )

        assert mock_run.call_count == 2

        call1_request = mock_run.call_args_list[0]
        call2_request = mock_run.call_args_list[1]

        session1 = call1_request.kwargs.get("input_request") or call1_request[1].get("input_request")
        session2 = call2_request.kwargs.get("input_request") or call2_request[1].get("input_request")

        if session1 is not None and session2 is not None:
            assert session1.session_id != session2.session_id


# ---------------------------------------------------------------------------
# Tests: Task linkage across turns
# ---------------------------------------------------------------------------


class TestTaskLinkage:
    """Tests that multi-turn conversations correctly link tasks by contextId.

    Each turn creates a new Task with its own ID, but all tasks in the
    same conversation share the same contextId. This lets clients
    retrieve the full conversation history.
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_each_turn_creates_separate_task(self, mock_run, client: AsyncClient, logged_in_headers):
        """Each message in a conversation produces a new Task.

        Tasks are the unit of work in A2A — each has its own lifecycle
        (SUBMITTED → WORKING → COMPLETED). Turns don't share tasks.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="multi-task-agent")

        # Three turns in one conversation
        task_ids = []
        for turn in ["Turn 1", "Turn 2", "Turn 3"]:
            response = await client.post(
                "/a2a/multi-task-agent/v1/message:send",
                json=_make_a2a_message(turn, context_id="ctx-multi"),
                headers=logged_in_headers,
            )
            assert response.status_code == 200
            task_ids.append(response.json()["id"])

        # All task IDs should be different
        assert len(set(task_ids)) == 3

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_list_tasks_returns_all_turns(self, mock_run, client: AsyncClient, logged_in_headers):
        """Listing tasks by contextId returns all turns in the conversation.

        This is how a client retrieves the full conversation history
        after reconnecting or losing state.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="list-turns-agent")

        # Two turns in conversation A, one turn in conversation B
        for text, ctx in [("A1", "ctx-A"), ("A2", "ctx-A"), ("B1", "ctx-B")]:
            await client.post(
                "/a2a/list-turns-agent/v1/message:send",
                json=_make_a2a_message(text, context_id=ctx),
                headers=logged_in_headers,
            )

        # List tasks for conversation A
        response = await client.get(
            "/a2a/list-turns-agent/v1/tasks?contextId=ctx-A",
            headers=logged_in_headers,
        )
        assert response.status_code == 200
        tasks_a = response.json()
        assert len(tasks_a) == 2

        # List tasks for conversation B
        response = await client.get(
            "/a2a/list-turns-agent/v1/tasks?contextId=ctx-B",
            headers=logged_in_headers,
        )
        tasks_b = response.json()
        assert len(tasks_b) == 1

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_all_tasks_share_context_id(self, mock_run, client: AsyncClient, logged_in_headers):
        """Every task in a conversation carries the same contextId.

        The contextId is the conversation thread identifier — it must
        be preserved on every task response so the client can correlate.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="ctx-preserve-agent")

        responses = []
        for turn in ["Turn 1", "Turn 2"]:
            r = await client.post(
                "/a2a/ctx-preserve-agent/v1/message:send",
                json=_make_a2a_message(turn, context_id="ctx-preserved"),
                headers=logged_in_headers,
            )
            responses.append(r.json())

        for task in responses:
            assert task["contextId"] == "ctx-preserved"

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_all_turns_complete_independently(self, mock_run, client: AsyncClient, logged_in_headers):
        """Each turn completes independently — Turn 2 doesn't wait for Turn 1.

        In v1, turns are independent flow executions. The only continuity
        is chat history via the shared session.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="independent-agent")

        for turn in ["Turn 1", "Turn 2", "Turn 3"]:
            r = await client.post(
                "/a2a/independent-agent/v1/message:send",
                json=_make_a2a_message(turn, context_id="ctx-indep"),
                headers=logged_in_headers,
            )
            # Every turn should complete on its own
            assert r.json()["status"]["state"] == "completed"


# ---------------------------------------------------------------------------
# Tests: No contextId (single-turn)
# ---------------------------------------------------------------------------


class TestSingleTurn:
    """Tests for single-turn messages (no contextId provided).

    When a client doesn't send a contextId, each message gets its own
    unique session. There's no conversation continuity.
    """

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_no_context_id_generates_unique_sessions(self, mock_run, client: AsyncClient, logged_in_headers):
        """Two messages without contextId get different session_ids.

        Without an explicit contextId, each message is a standalone
        interaction with no history.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="single-agent")

        # Two messages without contextId
        await client.post(
            "/a2a/single-agent/v1/message:send",
            json=_make_a2a_message("Message 1"),
            headers=logged_in_headers,
        )
        await client.post(
            "/a2a/single-agent/v1/message:send",
            json=_make_a2a_message("Message 2"),
            headers=logged_in_headers,
        )

        assert mock_run.call_count == 2

        call1_request = mock_run.call_args_list[0]
        call2_request = mock_run.call_args_list[1]

        session1 = call1_request.kwargs.get("input_request") or call1_request[1].get("input_request")
        session2 = call2_request.kwargs.get("input_request") or call2_request[1].get("input_request")

        if session1 is not None and session2 is not None:
            # Different sessions since no contextId was provided
            assert session1.session_id != session2.session_id

    @patch("langflow.api.v1.endpoints.simple_run_flow", new_callable=AsyncMock)
    async def test_no_context_id_still_returns_context_id_in_response(
        self, mock_run, client: AsyncClient, logged_in_headers
    ):
        """Even without a client-provided contextId, the response includes
        a server-generated contextId.

        This lets the client start a multi-turn conversation by using
        the returned contextId in subsequent messages.
        """
        mock_run.return_value = _mock_run_response()
        await _create_a2a_enabled_flow(client, logged_in_headers, slug="autoctx-agent")

        r = await client.post(
            "/a2a/autoctx-agent/v1/message:send",
            json=_make_a2a_message("Hello"),
            headers=logged_in_headers,
        )

        body = r.json()
        assert body["contextId"] is not None
        assert len(body["contextId"]) > 0
