"""A2A task lifecycle management.

Tracks A2A task state in memory (v1). Provides create, update, get,
list, cancel, and idempotent retry operations.

The task state machine follows the A2A spec:
    SUBMITTED → WORKING → COMPLETED
                        → FAILED
                        → INPUT_REQUIRED (Phase 5)
    Any non-terminal    → CANCELED

For v1, tasks are stored in memory (dict). This is acceptable for
team-scale use. A DB-backed store can be added later without changing
the interface.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

# Terminal states — tasks in these states won't be re-executed
_TERMINAL_STATES = frozenset({"completed", "canceled"})

# States that indicate the task is still in progress
_ACTIVE_STATES = frozenset({"submitted", "working", "input-required"})


class TaskManager:
    """Manages A2A task lifecycle with in-memory storage."""

    def __init__(self):
        # task_id → task dict
        self._tasks: dict[str, dict] = {}

    async def create_task(
        self,
        flow_id: str,
        context_id: str,
        task_id: str | None = None,
    ) -> dict:
        """Create a new task in SUBMITTED state.

        Args:
            flow_id: The Langflow flow being executed.
            context_id: The A2A conversation context.
            task_id: Optional caller-provided ID (for idempotent retry).

        Returns:
            The created task dict.
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc).isoformat()

        task = {
            "id": task_id,
            "kind": "task",
            "contextId": context_id,
            "status": {
                "state": "submitted",
                "timestamp": now,
            },
            "artifacts": [],
            "metadata": {
                "flowId": flow_id,
            },
            "_created_at": now,
            "_updated_at": now,
        }

        self._tasks[task_id] = task
        return task

    async def update_state(
        self,
        task_id: str,
        state: str,
        *,
        artifacts: list | None = None,
        error: str | None = None,
    ) -> dict:
        """Update a task's state.

        Args:
            task_id: The task to update.
            state: New state (submitted, working, completed, failed, canceled).
            artifacts: Output artifacts (for completed state).
            error: Error message (for failed state).

        Returns:
            The updated task dict.

        Raises:
            KeyError: If the task doesn't exist.
        """
        task = self._tasks.get(task_id)
        if task is None:
            msg = f"Task {task_id} not found"
            raise KeyError(msg)

        now = datetime.now(timezone.utc).isoformat()

        task["status"]["state"] = state
        task["status"]["timestamp"] = now
        task["_updated_at"] = now

        if artifacts is not None:
            task["artifacts"] = artifacts

        if error is not None:
            task["status"]["message"] = {
                "role": "agent",
                "parts": [{"kind": "text", "text": error}],
            }

        return task

    async def get_task(self, task_id: str) -> dict | None:
        """Retrieve a task by ID.

        Returns None if the task doesn't exist.
        """
        return self._tasks.get(task_id)

    async def list_tasks(self, context_id: str | None = None) -> list[dict]:
        """List tasks, optionally filtered by contextId.

        Args:
            context_id: If provided, only return tasks in this conversation.

        Returns:
            List of task dicts.
        """
        tasks = list(self._tasks.values())
        if context_id is not None:
            tasks = [t for t in tasks if t.get("contextId") == context_id]
        return tasks

    async def handle_retry(self, task_id: str) -> dict | None:
        """Handle an idempotent retry for a given taskId.

        Returns:
            - The existing task if it's completed or still active (don't re-execute)
            - None if the task doesn't exist or failed (allow re-execution)
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None

        state = task["status"]["state"]

        # Terminal (completed, canceled) or active (working) → return cached
        if state in _TERMINAL_STATES or state in _ACTIVE_STATES:
            # Failed tasks should be retried
            return task

        # Failed → allow re-execution
        return None
