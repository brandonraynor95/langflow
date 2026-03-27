"""Unit tests for the A2A task manager (lifecycle management).

Tests the task state machine that tracks A2A task lifecycle:
create → SUBMITTED → WORKING → COMPLETED/FAILED/CANCELED.

Also tests idempotent retry behavior: re-sending the same taskId
returns cached results for completed tasks.

These tests use the in-memory task store — no database required.
"""

import pytest

from langflow.api.a2a.task_manager import TaskManager

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_manager():
    """Create a TaskManager backed by in-memory storage for testing."""
    return TaskManager()


# ---------------------------------------------------------------------------
# Tests: Task creation
# ---------------------------------------------------------------------------


class TestTaskCreation:
    """Tests for creating new A2A tasks."""

    async def test_create_task_returns_submitted_state(self, task_manager):
        """A newly created task starts in SUBMITTED state.

        This is the initial state before any flow execution begins.
        """
        task = await task_manager.create_task(
            flow_id="flow-123",
            context_id="ctx-abc",
        )
        assert task["id"] is not None
        assert task["status"]["state"] == "submitted"
        assert task["contextId"] == "ctx-abc"

    async def test_create_task_with_explicit_id(self, task_manager):
        """A task can be created with a caller-provided ID.

        This enables the A2A idempotent retry pattern — the client
        sends the same taskId to retry a failed request.
        """
        task = await task_manager.create_task(
            flow_id="flow-123",
            context_id="ctx-abc",
            task_id="explicit-task-id",
        )
        assert task["id"] == "explicit-task-id"

    async def test_create_task_auto_generates_id(self, task_manager):
        """When no task_id is provided, one is auto-generated."""
        task = await task_manager.create_task(
            flow_id="flow-123",
            context_id="ctx-abc",
        )
        assert task["id"] is not None
        assert len(task["id"]) > 0


# ---------------------------------------------------------------------------
# Tests: State transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """Tests for the A2A task state machine.

    Valid transitions:
    - SUBMITTED → WORKING (flow execution starts)
    - WORKING → COMPLETED (flow finishes successfully)
    - WORKING → FAILED (flow errors)
    - Any non-terminal → CANCELED (cancellation requested)
    """

    async def test_submitted_to_working(self, task_manager):
        """Task moves to WORKING when flow execution begins."""
        task = await task_manager.create_task(flow_id="f", context_id="c")
        updated = await task_manager.update_state(task["id"], "working")
        assert updated["status"]["state"] == "working"

    async def test_working_to_completed(self, task_manager):
        """Task moves to COMPLETED when flow finishes successfully."""
        task = await task_manager.create_task(flow_id="f", context_id="c")
        await task_manager.update_state(task["id"], "working")

        artifacts = [{"parts": [{"kind": "text", "text": "Result"}]}]
        updated = await task_manager.update_state(
            task["id"], "completed", artifacts=artifacts
        )

        assert updated["status"]["state"] == "completed"
        assert updated["artifacts"] == artifacts

    async def test_working_to_failed(self, task_manager):
        """Task moves to FAILED when flow errors."""
        task = await task_manager.create_task(flow_id="f", context_id="c")
        await task_manager.update_state(task["id"], "working")

        updated = await task_manager.update_state(
            task["id"], "failed", error="Flow execution failed: division by zero"
        )

        assert updated["status"]["state"] == "failed"
        assert "division by zero" in updated["status"]["message"]["parts"][0]["text"]

    async def test_cancel_working_task(self, task_manager):
        """A working task can be canceled."""
        task = await task_manager.create_task(flow_id="f", context_id="c")
        await task_manager.update_state(task["id"], "working")

        updated = await task_manager.update_state(task["id"], "canceled")
        assert updated["status"]["state"] == "canceled"

    async def test_cancel_submitted_task(self, task_manager):
        """A submitted task (not yet executing) can be canceled."""
        task = await task_manager.create_task(flow_id="f", context_id="c")
        updated = await task_manager.update_state(task["id"], "canceled")
        assert updated["status"]["state"] == "canceled"


# ---------------------------------------------------------------------------
# Tests: Task retrieval
# ---------------------------------------------------------------------------


class TestTaskRetrieval:
    """Tests for reading task state."""

    async def test_get_task_by_id(self, task_manager):
        """A task can be retrieved by its ID."""
        task = await task_manager.create_task(flow_id="f", context_id="c")
        retrieved = await task_manager.get_task(task["id"])
        assert retrieved is not None
        assert retrieved["id"] == task["id"]

    async def test_get_nonexistent_task_returns_none(self, task_manager):
        """Requesting a task that doesn't exist returns None."""
        retrieved = await task_manager.get_task("nonexistent-id")
        assert retrieved is None

    async def test_list_tasks_by_context(self, task_manager):
        """Tasks can be listed by contextId to see all turns in a conversation."""
        await task_manager.create_task(flow_id="f", context_id="ctx-1", task_id="t1")
        await task_manager.create_task(flow_id="f", context_id="ctx-1", task_id="t2")
        await task_manager.create_task(flow_id="f", context_id="ctx-2", task_id="t3")

        tasks = await task_manager.list_tasks(context_id="ctx-1")
        assert len(tasks) == 2
        task_ids = {t["id"] for t in tasks}
        assert task_ids == {"t1", "t2"}

    async def test_list_all_tasks(self, task_manager):
        """All tasks can be listed when no filter is provided."""
        await task_manager.create_task(flow_id="f", context_id="c1", task_id="t1")
        await task_manager.create_task(flow_id="f", context_id="c2", task_id="t2")

        tasks = await task_manager.list_tasks()
        assert len(tasks) == 2


# ---------------------------------------------------------------------------
# Tests: Idempotent retry
# ---------------------------------------------------------------------------


class TestIdempotentRetry:
    """Tests for the idempotent retry pattern.

    When a client re-sends a message with the same taskId:
    - If the task completed: return the cached result (don't re-execute)
    - If the task failed: allow re-execution
    - If the task is still running: return current state
    """

    async def test_retry_completed_task_returns_cached(self, task_manager):
        """Re-sending a completed task's ID returns the cached result.

        This prevents duplicate execution when a client retries after
        a network timeout (the original request may have succeeded).
        """
        task = await task_manager.create_task(
            flow_id="f", context_id="c", task_id="retry-me"
        )
        await task_manager.update_state(task["id"], "working")
        artifacts = [{"parts": [{"kind": "text", "text": "Original result"}]}]
        await task_manager.update_state(task["id"], "completed", artifacts=artifacts)

        # Retry returns the existing task (not None)
        existing = await task_manager.handle_retry("retry-me")
        assert existing is not None
        assert existing["status"]["state"] == "completed"
        assert existing["artifacts"] == artifacts

    async def test_retry_failed_task_returns_none(self, task_manager):
        """Re-sending a failed task's ID returns None (allow re-execution).

        Failed tasks should be retried — the failure may have been
        transient (network error, rate limit, etc.).
        """
        task = await task_manager.create_task(
            flow_id="f", context_id="c", task_id="retry-failed"
        )
        await task_manager.update_state(task["id"], "working")
        await task_manager.update_state(task["id"], "failed", error="Timeout")

        existing = await task_manager.handle_retry("retry-failed")
        assert existing is None  # Allow re-execution

    async def test_retry_working_task_returns_current(self, task_manager):
        """Re-sending a running task's ID returns current state.

        The client should see that the task is still in progress
        rather than starting a duplicate execution.
        """
        task = await task_manager.create_task(
            flow_id="f", context_id="c", task_id="in-progress"
        )
        await task_manager.update_state(task["id"], "working")

        existing = await task_manager.handle_retry("in-progress")
        assert existing is not None
        assert existing["status"]["state"] == "working"

    async def test_retry_unknown_task_returns_none(self, task_manager):
        """A taskId that was never created returns None."""
        existing = await task_manager.handle_retry("never-existed")
        assert existing is None
