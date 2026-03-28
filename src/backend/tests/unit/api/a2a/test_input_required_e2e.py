"""End-to-end test for INPUT_REQUIRED via message:send with simulated tool call.

This test exercises the complete INPUT_REQUIRED flow through HTTP endpoints,
with the mock simple_run_flow simulating the agent calling request_input
during execution.

Flow:
1. Client sends POST /message:send — mock starts "executing"
2. Mock calls task_manager.request_input() → task → INPUT_REQUIRED
3. Client sees task is INPUT_REQUIRED via GET /tasks/{id}
4. Client sends follow-up POST /message:send with same taskId
5. Follow-up resolves the pending input
6. Mock completes — task → COMPLETED

This is the closest we can get to a real end-to-end test without
an actual LLM calling the request_input tool.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from langflow.api.a2a.request_input_tool import create_request_input_tool
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


def _mock_run_response(text: str):
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
# Tests
# ---------------------------------------------------------------------------


class TestInputRequiredE2E:
    """End-to-end test simulating an agent calling request_input mid-execution.

    The mock simple_run_flow:
    1. Calls task_manager.request_input() to simulate the agent asking
    2. Waits for the asyncio.Event to be resolved (client follow-up)
    3. Returns a response that includes the client's answer

    Meanwhile, the test:
    1. Sends the initial message (which blocks in the mock)
    2. In a separate task, polls until INPUT_REQUIRED, then sends follow-up
    3. Verifies the final response includes the resolved answer
    """

    async def test_input_required_resolved_via_follow_up(self, client: AsyncClient, logged_in_headers):
        """Full round-trip: send → INPUT_REQUIRED → follow-up → COMPLETED.

        This tests:
        - Task transitions: SUBMITTED → WORKING → INPUT_REQUIRED → WORKING → COMPLETED
        - Follow-up routing: message:send with taskId resolves pending input
        - The agent receives the client's response and uses it
        """
        from langflow.api.a2a.router import _task_manager

        await _create_a2a_enabled_flow(client, logged_in_headers, slug="e2e-ir-agent")

        # Track the tool info so we can verify the flow
        tool_event = asyncio.Event()
        tool_response_holder: dict = {}

        async def mock_simple_run_flow(
            *,
            flow=None,
            input_request=None,
            stream=False,
            api_key_user=None,
            event_manager=None,
            context=None,
            run_id=None,
        ):
            """Simulate an agent that calls request_input mid-execution.

            1. Signals INPUT_REQUIRED via task_manager
            2. Waits for resolution
            3. Returns a response incorporating the client's answer
            """
            # Find the task that was created for this execution
            # (the router creates the task before calling _execute_flow)
            all_tasks = await _task_manager.list_tasks()
            current_task = all_tasks[-1] if all_tasks else None

            if current_task:
                task_id = current_task["id"]

                # Simulate the agent calling request_input
                await _task_manager.request_input(
                    task_id,
                    "Which environment should I deploy to?",
                    tool_event,
                    tool_response_holder,
                )

                # Wait for the client to respond (with timeout)
                await asyncio.wait_for(tool_event.wait(), timeout=5.0)
                client_answer = tool_response_holder.get("response", "unknown")

                return _mock_run_response(f"Deployed to {client_answer} successfully")

            return _mock_run_response("No task found")

        with patch(
            "langflow.api.v1.endpoints.simple_run_flow",
            side_effect=mock_simple_run_flow,
        ):
            # Send the initial message in a background task
            # (it will block until INPUT_REQUIRED is resolved)
            async def send_initial():
                return await client.post(
                    "/a2a/e2e-ir-agent/v1/message:send",
                    json={
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": "Deploy my app"}],
                            "contextId": "ctx-e2e",
                        },
                    },
                    headers=logged_in_headers,
                )

            initial_task = asyncio.create_task(send_initial())

            # Wait for the task to reach INPUT_REQUIRED
            for _ in range(50):  # 50 * 0.1s = 5s max
                await asyncio.sleep(0.1)
                all_tasks = await _task_manager.list_tasks()
                if all_tasks and all_tasks[-1]["status"]["state"] == "input-required":
                    break

            # Verify the task is in INPUT_REQUIRED
            all_tasks = await _task_manager.list_tasks()
            assert len(all_tasks) > 0
            ir_task = all_tasks[-1]
            assert ir_task["status"]["state"] == "input-required"

            # Verify the question is stored
            question_parts = ir_task["status"]["message"]["parts"]
            assert any("environment" in p["text"].lower() for p in question_parts)

            # Send the follow-up with the answer
            follow_up = await client.post(
                "/a2a/e2e-ir-agent/v1/message:send",
                json={
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "prod-us"}],
                    },
                    "taskId": ir_task["id"],
                },
                headers=logged_in_headers,
            )
            assert follow_up.status_code == 200

            # Wait for the initial request to complete
            response = await asyncio.wait_for(initial_task, timeout=5.0)

            assert response.status_code == 200
            body = response.json()
            assert body["status"]["state"] == "completed"
            # The response should include the client's answer
            artifact_text = body["artifacts"][0]["parts"][0]["text"]
            assert "prod-us" in artifact_text

    async def test_poll_shows_input_required_with_question(self, client: AsyncClient, logged_in_headers):
        """GET /tasks/{id} shows INPUT_REQUIRED state with the agent's question.

        This is how a non-streaming client discovers that the agent
        needs clarification.
        """
        from langflow.api.a2a.router import _task_manager

        await _create_a2a_enabled_flow(client, logged_in_headers, slug="poll-e2e-agent")

        tool_event = asyncio.Event()
        tool_response_holder: dict = {}

        async def mock_simple_run_flow(
            *,
            flow=None,
            input_request=None,
            stream=False,
            api_key_user=None,
            event_manager=None,
            context=None,
            run_id=None,
        ):
            all_tasks = await _task_manager.list_tasks()
            current_task = all_tasks[-1]
            await _task_manager.request_input(
                current_task["id"],
                "What database?",
                tool_event,
                tool_response_holder,
            )
            await asyncio.wait_for(tool_event.wait(), timeout=5.0)
            return _mock_run_response(f"Using {tool_response_holder.get('response', '?')}")

        with patch(
            "langflow.api.v1.endpoints.simple_run_flow",
            side_effect=mock_simple_run_flow,
        ):
            # Start execution in background
            async def send_msg():
                return await client.post(
                    "/a2a/poll-e2e-agent/v1/message:send",
                    json={
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": "Set up DB"}],
                            "contextId": "ctx-poll-e2e",
                        },
                    },
                    headers=logged_in_headers,
                )

            bg_task = asyncio.create_task(send_msg())

            # Wait for INPUT_REQUIRED
            task_id = None
            for _ in range(50):
                await asyncio.sleep(0.1)
                all_tasks = await _task_manager.list_tasks()
                if all_tasks and all_tasks[-1]["status"]["state"] == "input-required":
                    task_id = all_tasks[-1]["id"]
                    break

            assert task_id is not None

            # Poll the task via HTTP
            poll_response = await client.get(
                f"/a2a/poll-e2e-agent/v1/tasks/{task_id}",
                headers=logged_in_headers,
            )
            assert poll_response.status_code == 200
            poll_body = poll_response.json()
            assert poll_body["status"]["state"] == "input-required"
            assert "database" in poll_body["status"]["message"]["parts"][0]["text"].lower()

            # Resolve and clean up
            await _task_manager.resolve_input(task_id, "postgres")
            await asyncio.wait_for(bg_task, timeout=5.0)
