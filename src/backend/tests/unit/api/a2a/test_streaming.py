"""Unit tests for the A2A SSE stream bridge.

Tests the translation from Langflow's internal event format to A2A
SSE events (TaskStatusUpdateEvent, TaskArtifactUpdateEvent).

Langflow events arrive as JSON strings with {"event": type, "data": ...}.
The bridge converts these to A2A-compliant SSE data lines.

Event mapping:
- "token"      → TaskArtifactUpdateEvent (partial text, append=True)
- "end_vertex" → TaskStatusUpdateEvent (state=working, progress message)
- "end"        → TaskStatusUpdateEvent (state=completed) + final artifact
- "error"      → TaskStatusUpdateEvent (state=failed)

These are pure async tests — no HTTP, no database.
"""

import asyncio
import json

import pytest

from langflow.api.a2a.streaming import A2AStreamBridge

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_langflow_event(event_type: str, data: dict | str) -> str:
    """Create a Langflow event string as the EventManager produces it."""
    return json.dumps({"event": event_type, "data": data}) + "\n\n"


async def _collect_a2a_events(bridge: A2AStreamBridge, count: int, timeout: float = 1.0) -> list[dict]:
    """Collect A2A events from the bridge's output queue."""
    events = []
    try:
        for _ in range(count):
            event = await asyncio.wait_for(bridge.output_queue.get(), timeout=timeout)
            if event is None:
                break
            events.append(json.loads(event) if isinstance(event, str) else event)
    except asyncio.TimeoutError:
        pass
    return events


# ---------------------------------------------------------------------------
# Tests: Token streaming → artifact updates
# ---------------------------------------------------------------------------


class TestTokenStreaming:
    """Tests that LLM token events are translated to A2A artifact updates.

    Tokens are the most frequent event during streaming — each token
    from the LLM produces an artifact update with append=True.
    """

    async def test_token_event_produces_artifact_update(self):
        """A 'token' event from the LLM becomes a TaskArtifactUpdateEvent.

        The artifact contains the token text and append=True to indicate
        the client should append to the existing output.
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        langflow_event = _make_langflow_event("token", {"chunk": "Hello"})
        await bridge.process_langflow_event(langflow_event)

        events = await _collect_a2a_events(bridge, 1)
        assert len(events) == 1
        assert events[0]["kind"] == "artifact-update"
        assert events[0]["taskId"] == "task-1"
        assert events[0]["artifact"]["parts"][0]["text"] == "Hello"
        assert events[0]["append"] is True

    async def test_multiple_tokens_produce_multiple_updates(self):
        """Each token event produces a separate artifact update.

        The client accumulates them to build the full response.
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        for token in ["Hello", " world", "!"]:
            await bridge.process_langflow_event(
                _make_langflow_event("token", {"chunk": token})
            )

        events = await _collect_a2a_events(bridge, 3)
        assert len(events) == 3
        texts = [e["artifact"]["parts"][0]["text"] for e in events]
        assert texts == ["Hello", " world", "!"]


# ---------------------------------------------------------------------------
# Tests: Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    """Tests that flow lifecycle events are translated to A2A status updates."""

    async def test_end_event_produces_completed_status(self):
        """An 'end' event means the flow finished → COMPLETED status.

        This is the terminal event — the client knows the task is done.
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        end_data = {"result": {"outputs": [{"inputs": {}, "outputs": []}]}}
        await bridge.process_langflow_event(
            _make_langflow_event("end", end_data)
        )

        events = await _collect_a2a_events(bridge, 1)
        assert len(events) >= 1
        # Find the status update event
        status_events = [e for e in events if e.get("kind") == "status-update"]
        assert len(status_events) == 1
        assert status_events[0]["status"]["state"] == "completed"
        assert status_events[0]["final"] is True

    async def test_error_event_produces_failed_status(self):
        """An 'error' event means the flow failed → FAILED status.

        The error message is included so the client can diagnose.
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        await bridge.process_langflow_event(
            _make_langflow_event("error", {"error": "LLM rate limit exceeded"})
        )

        events = await _collect_a2a_events(bridge, 1)
        assert len(events) == 1
        assert events[0]["kind"] == "status-update"
        assert events[0]["status"]["state"] == "failed"
        assert "rate limit" in events[0]["status"]["message"]["parts"][0]["text"].lower()

    async def test_end_vertex_produces_working_progress(self):
        """An 'end_vertex' event means a graph step completed → progress update.

        This keeps the client informed during long-running flows.
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        await bridge.process_langflow_event(
            _make_langflow_event("end_vertex", {"build_data": "vertex-abc"})
        )

        events = await _collect_a2a_events(bridge, 1)
        assert len(events) == 1
        assert events[0]["kind"] == "status-update"
        assert events[0]["status"]["state"] == "working"


# ---------------------------------------------------------------------------
# Tests: Stream lifecycle
# ---------------------------------------------------------------------------


class TestStreamLifecycle:
    """Tests for the stream bridge lifecycle management."""

    async def test_finish_sends_none_sentinel(self):
        """Calling finish() puts None on the output queue to signal stream end."""
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")
        await bridge.finish()

        sentinel = await asyncio.wait_for(bridge.output_queue.get(), timeout=1.0)
        assert sentinel is None

    async def test_full_lifecycle(self):
        """A complete token→end flow produces the right event sequence.

        Simulates a real streaming execution: tokens arrive, then
        the flow completes.
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        # Tokens
        await bridge.process_langflow_event(
            _make_langflow_event("token", {"chunk": "Hello"})
        )
        await bridge.process_langflow_event(
            _make_langflow_event("token", {"chunk": " world"})
        )

        # End
        await bridge.process_langflow_event(
            _make_langflow_event("end", {"result": {}})
        )

        events = await _collect_a2a_events(bridge, 10)

        # Should have: 2 artifact updates + 1 completed status
        artifact_events = [e for e in events if e.get("kind") == "artifact-update"]
        status_events = [e for e in events if e.get("kind") == "status-update"]

        assert len(artifact_events) == 2
        assert len(status_events) >= 1
        assert status_events[-1]["status"]["state"] == "completed"

    async def test_unknown_events_are_ignored(self):
        """Events the bridge doesn't recognize are silently ignored.

        Langflow may emit events we don't need (build_start, etc.).
        """
        bridge = A2AStreamBridge(task_id="task-1", context_id="ctx-1")

        await bridge.process_langflow_event(
            _make_langflow_event("build_start", {"vertex_id": "v1"})
        )

        # Should produce no output events
        events = await _collect_a2a_events(bridge, 1, timeout=0.1)
        assert len(events) == 0
