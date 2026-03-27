"""Shared fixtures for A2A tests."""

import pytest


@pytest.fixture(autouse=True)
def _reset_a2a_task_manager():
    """Reset the module-level task manager between tests.

    The task manager is a module-level singleton for v1 (in-memory).
    Tests must start with a clean state to avoid cross-test contamination.
    """
    from langflow.api.a2a.router import _task_manager

    _task_manager._tasks.clear()
    _task_manager._pending_inputs.clear()
    yield
    _task_manager._tasks.clear()
    _task_manager._pending_inputs.clear()
