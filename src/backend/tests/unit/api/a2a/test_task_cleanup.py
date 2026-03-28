"""Tests for task TTL cleanup (Phase 6).

Verifies that the TaskManager prunes expired tasks while preserving
active ones. This prevents unbounded memory growth from accumulated
task records.

Rules:
- Completed/Failed/Canceled tasks older than TTL → pruned
- Working/Input-Required tasks → NEVER pruned (even if old)
- Submitted tasks older than TTL → pruned (likely abandoned)
"""

from datetime import datetime, timezone, timedelta

import pytest

from langflow.api.a2a.task_manager import TaskManager

pytestmark = pytest.mark.asyncio


@pytest.fixture
def task_manager():
    return TaskManager()


class TestTaskCleanup:
    """Tests for cleanup_expired_tasks()."""

    async def test_completed_task_pruned_after_ttl(self, task_manager):
        """A completed task older than the TTL is removed.

        This is the normal case — old finished work is cleaned up.
        """
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="old-done")
        await task_manager.update_state(task["id"], "working")
        await task_manager.update_state(task["id"], "completed")

        # Backdate the task
        task_manager._tasks["old-done"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=25)
        ).isoformat()

        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)  # 24h

        assert pruned == 1
        assert await task_manager.get_task("old-done") is None

    async def test_failed_task_pruned_after_ttl(self, task_manager):
        """A failed task older than the TTL is removed."""
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="old-fail")
        await task_manager.update_state(task["id"], "working")
        await task_manager.update_state(task["id"], "failed", error="boom")

        task_manager._tasks["old-fail"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=25)
        ).isoformat()

        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)
        assert pruned == 1

    async def test_recent_completed_task_not_pruned(self, task_manager):
        """A completed task newer than the TTL is kept.

        Recent tasks may still be polled by clients for results.
        """
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="new-done")
        await task_manager.update_state(task["id"], "working")
        await task_manager.update_state(task["id"], "completed")
        # _updated_at is now (within TTL)

        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)
        assert pruned == 0
        assert await task_manager.get_task("new-done") is not None

    async def test_working_task_never_pruned(self, task_manager):
        """A WORKING task is never pruned, even if old.

        It's still executing — pruning it would lose state.
        """
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="old-working")
        await task_manager.update_state(task["id"], "working")

        task_manager._tasks["old-working"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=48)
        ).isoformat()

        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)
        assert pruned == 0
        assert await task_manager.get_task("old-working") is not None

    async def test_input_required_task_never_pruned(self, task_manager):
        """An INPUT_REQUIRED task is never pruned, even if old.

        It's waiting for client input — the client may still respond.
        """
        task = await task_manager.create_task(flow_id="f", context_id="c", task_id="old-ir")
        await task_manager.update_state(task["id"], "input-required")

        task_manager._tasks["old-ir"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=48)
        ).isoformat()

        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)
        assert pruned == 0
        assert await task_manager.get_task("old-ir") is not None

    async def test_mixed_tasks_only_expired_pruned(self, task_manager):
        """Only expired terminal tasks are pruned — others are kept.

        Verifies selective cleanup across a mix of task states and ages.
        """
        # Old completed → prune
        t1 = await task_manager.create_task(flow_id="f", context_id="c", task_id="t1")
        await task_manager.update_state(t1["id"], "completed")
        task_manager._tasks["t1"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=25)
        ).isoformat()

        # New completed → keep
        t2 = await task_manager.create_task(flow_id="f", context_id="c", task_id="t2")
        await task_manager.update_state(t2["id"], "completed")

        # Old working → keep (active)
        t3 = await task_manager.create_task(flow_id="f", context_id="c", task_id="t3")
        await task_manager.update_state(t3["id"], "working")
        task_manager._tasks["t3"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=25)
        ).isoformat()

        # Old canceled → prune
        t4 = await task_manager.create_task(flow_id="f", context_id="c", task_id="t4")
        await task_manager.update_state(t4["id"], "canceled")
        task_manager._tasks["t4"]["_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=25)
        ).isoformat()

        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)
        assert pruned == 2  # t1 and t4

        assert await task_manager.get_task("t1") is None  # pruned
        assert await task_manager.get_task("t2") is not None  # kept (recent)
        assert await task_manager.get_task("t3") is not None  # kept (active)
        assert await task_manager.get_task("t4") is None  # pruned

    async def test_cleanup_returns_count(self, task_manager):
        """cleanup_expired_tasks returns the number of tasks pruned."""
        pruned = await task_manager.cleanup_expired_tasks(ttl_seconds=86400)
        assert pruned == 0  # No tasks at all
