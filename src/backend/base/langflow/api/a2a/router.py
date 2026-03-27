"""FastAPI router for A2A protocol endpoints.

Two routers are defined:
1. `a2a_router` — Public A2A protocol endpoints mounted at /a2a/{agent_slug}/
2. `a2a_config_router` — Internal admin endpoints for managing A2A config

The instance-level toggle LANGFLOW_A2A_ENABLED controls whether the public
A2A endpoints are active. When disabled, all public routes return 404.
"""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from lfx.log.logger import logger
from pydantic import BaseModel
from sqlmodel import select

from langflow.api.a2a.agent_card import generate_agent_card
from langflow.api.a2a.config import validate_a2a_slug, validate_flow_eligible_for_a2a
from langflow.api.a2a.flow_adapter import translate_inbound, translate_outbound
from langflow.api.a2a.task_manager import TaskManager
from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.flow.model import Flow

# Module-level task manager instance (in-memory for v1)
_task_manager = TaskManager()

# ---------------------------------------------------------------------------
# Pydantic models for request/response
# ---------------------------------------------------------------------------


class A2AConfigUpdate(BaseModel):
    """Request body for updating A2A config on a flow."""

    a2a_enabled: bool | None = None
    a2a_agent_slug: str | None = None
    a2a_name: str | None = None
    a2a_description: str | None = None


class A2AConfigRead(BaseModel):
    """Response body for reading A2A config."""

    a2a_enabled: bool
    a2a_agent_slug: str | None
    a2a_name: str | None
    a2a_description: str | None
    a2a_input_mode: str
    a2a_output_mode: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _a2a_is_enabled() -> bool:
    """Check the instance-level LANGFLOW_A2A_ENABLED toggle."""
    return os.environ.get("LANGFLOW_A2A_ENABLED", "true").lower() in ("true", "1", "yes")


async def _get_flow_by_slug(session, slug: str) -> Flow | None:
    """Look up a flow by its a2a_agent_slug."""
    stmt = select(Flow).where(
        Flow.a2a_agent_slug == slug,
        Flow.a2a_enabled == True,  # noqa: E712
    )
    result = await session.exec(stmt)
    return result.first()


# ---------------------------------------------------------------------------
# Public A2A protocol router
# ---------------------------------------------------------------------------

a2a_router = APIRouter(tags=["a2a"])


@a2a_router.get("/a2a/{agent_slug}/.well-known/agent-card.json")
async def get_agent_card(
    agent_slug: str,
    session: DbSession,
):
    """Serve the public AgentCard for an A2A-enabled flow.

    This endpoint does NOT require authentication — it's how external
    agents discover what this agent can do. The A2A spec defines this
    as a publicly accessible discovery endpoint.

    Returns 404 if:
    - LANGFLOW_A2A_ENABLED is false (instance-level kill switch)
    - No flow exists with this slug
    - The flow has a2a_enabled=False
    """
    if not _a2a_is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A2A is not enabled")

    flow = await _get_flow_by_slug(session, agent_slug)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    base_url = f"/a2a/{agent_slug}"
    card = generate_agent_card(flow, base_url=base_url)
    return card


@a2a_router.get("/a2a/{agent_slug}/v1/card")
async def get_extended_agent_card(
    agent_slug: str,
    session: DbSession,
    current_user: CurrentActiveUser,  # noqa: ARG001
):
    """Serve the extended AgentCard (auth-gated).

    Contains full skill schemas and detailed capability info.
    Requires authentication.
    """
    if not _a2a_is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A2A is not enabled")

    flow = await _get_flow_by_slug(session, agent_slug)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    base_url = f"/a2a/{agent_slug}"
    card = generate_agent_card(flow, base_url=base_url)
    # Extended card can include additional details in the future
    card["extended"] = True
    return card


# ---------------------------------------------------------------------------
# message:send endpoint
# ---------------------------------------------------------------------------


@a2a_router.post("/a2a/{agent_slug}/v1/message:send")
async def message_send(
    agent_slug: str,
    body: dict[str, Any],
    session: DbSession,
    current_user: CurrentActiveUser,  # noqa: ARG001
):
    """Send an A2A message to a Langflow agent (synchronous).

    Executes the flow and returns a completed/failed Task.

    The request body follows the A2A protocol:
    {
        "message": { "role": "user", "parts": [...], "contextId": "..." },
        "taskId": "optional-for-retry"
    }
    """
    if not _a2a_is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A2A is not enabled")

    flow = await _get_flow_by_slug(session, agent_slug)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    message = body.get("message", {})
    requested_task_id = body.get("taskId")
    context_id = message.get("contextId") or str(uuid.uuid4())

    # Idempotent retry check
    if requested_task_id:
        existing = await _task_manager.handle_retry(requested_task_id)
        if existing is not None:
            return existing

    # Create task
    task = await _task_manager.create_task(
        flow_id=str(flow.id),
        context_id=context_id,
        task_id=requested_task_id,
    )
    task_id = task["id"]

    try:
        # Translate A2A message → Langflow inputs
        flow_secret = str(flow.id)  # Use flow ID as HMAC secret for v1
        flow_inputs = await translate_inbound(message, flow_secret=flow_secret)

        # Update to WORKING
        await _task_manager.update_state(task_id, "working")

        # Execute the flow
        result = await _execute_flow(flow, flow_inputs, session)

        # Translate outputs → A2A artifacts
        artifacts = await translate_outbound(result.outputs or [])

        # Update to COMPLETED
        task = await _task_manager.update_state(task_id, "completed", artifacts=artifacts)
        task["contextId"] = context_id
        return task

    except Exception as e:
        logger.exception(f"A2A flow execution failed for task {task_id}: {e}")
        task = await _task_manager.update_state(task_id, "failed", error=str(e))
        task["contextId"] = context_id
        return task


async def _execute_flow(flow: Flow, flow_inputs: dict, session) -> Any:
    """Execute a Langflow flow with the given inputs.

    Wraps simple_run_flow() with the right parameters.
    """
    from langflow.api.v1.endpoints import simple_run_flow
    from langflow.api.v1.schemas import SimplifiedAPIRequest

    input_request = SimplifiedAPIRequest(
        input_value=flow_inputs["input_value"],
        input_type=flow_inputs.get("input_type", "chat"),
        output_type=flow_inputs.get("output_type", "chat"),
        tweaks=flow_inputs.get("tweaks"),
        session_id=flow_inputs.get("session_id"),
    )

    return await simple_run_flow(
        flow=flow,
        input_request=input_request,
        stream=False,
    )


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------


@a2a_router.get("/a2a/{agent_slug}/v1/tasks/{task_id}")
async def get_task(
    agent_slug: str,  # noqa: ARG001
    task_id: str,
    session: DbSession,  # noqa: ARG001
    current_user: CurrentActiveUser,  # noqa: ARG001
):
    """Get the current state of an A2A task.

    Used for polling when the client doesn't have an SSE connection.
    """
    task = await _task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@a2a_router.get("/a2a/{agent_slug}/v1/tasks")
async def list_tasks(
    agent_slug: str,  # noqa: ARG001
    session: DbSession,  # noqa: ARG001
    current_user: CurrentActiveUser,  # noqa: ARG001
    contextId: str | None = Query(None),  # noqa: N803
):
    """List A2A tasks, optionally filtered by contextId."""
    return await _task_manager.list_tasks(context_id=contextId)


@a2a_router.post("/a2a/{agent_slug}/v1/tasks/{task_id}:cancel")
async def cancel_task(
    agent_slug: str,  # noqa: ARG001
    task_id: str,
    session: DbSession,  # noqa: ARG001
    current_user: CurrentActiveUser,  # noqa: ARG001
):
    """Cancel an A2A task (best-effort)."""
    task = await _task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        updated = await _task_manager.update_state(task_id, "canceled")
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")  # noqa: B904
    return updated


# ---------------------------------------------------------------------------
# Internal A2A config router (mounted under /api/v1/)
# ---------------------------------------------------------------------------

a2a_config_router = APIRouter(prefix="/flows", tags=["a2a-config"])


@a2a_config_router.put("/{flow_id}/a2a-config")
async def update_a2a_config(
    flow_id: UUID,
    config: A2AConfigUpdate,
    session: DbSession,
    current_user: CurrentActiveUser,
):
    """Enable or update A2A configuration on a flow.

    Validates:
    - The flow exists and belongs to the current user
    - The slug format is valid
    - The slug is unique (no other flow uses it)
    - The flow is eligible for A2A (has Agent/LLM components)
    """
    # Load the flow
    flow = await session.get(Flow, flow_id)
    if not flow or flow.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    # Validate slug if provided
    if config.a2a_agent_slug is not None:
        try:
            validate_a2a_slug(config.a2a_agent_slug)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            ) from e

        # Check slug uniqueness
        existing = await session.exec(
            select(Flow).where(
                Flow.a2a_agent_slug == config.a2a_agent_slug,
                Flow.id != flow_id,
            )
        )
        if existing.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent slug '{config.a2a_agent_slug}' is already in use by another flow.",
            )

    # Validate flow eligibility if enabling
    if config.a2a_enabled:
        if not validate_flow_eligible_for_a2a(flow.data):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This flow is not eligible for A2A exposure. "
                "It must contain an Agent or LLM component.",
            )

    # Apply updates
    if config.a2a_enabled is not None:
        flow.a2a_enabled = config.a2a_enabled
    if config.a2a_agent_slug is not None:
        flow.a2a_agent_slug = config.a2a_agent_slug
    if config.a2a_name is not None:
        flow.a2a_name = config.a2a_name
    if config.a2a_description is not None:
        flow.a2a_description = config.a2a_description

    session.add(flow)
    await session.flush()
    await session.refresh(flow)

    return A2AConfigRead(
        a2a_enabled=flow.a2a_enabled or False,
        a2a_agent_slug=flow.a2a_agent_slug,
        a2a_name=flow.a2a_name,
        a2a_description=flow.a2a_description,
        a2a_input_mode=getattr(flow, "a2a_input_mode", "chat"),
        a2a_output_mode=getattr(flow, "a2a_output_mode", "text"),
    )


@a2a_config_router.get("/{flow_id}/a2a-config")
async def get_a2a_config(
    flow_id: UUID,
    session: DbSession,
    current_user: CurrentActiveUser,
):
    """Read the A2A configuration for a flow."""
    flow = await session.get(Flow, flow_id)
    if not flow or flow.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    return A2AConfigRead(
        a2a_enabled=flow.a2a_enabled or False,
        a2a_agent_slug=flow.a2a_agent_slug,
        a2a_name=flow.a2a_name,
        a2a_description=flow.a2a_description,
        a2a_input_mode=getattr(flow, "a2a_input_mode", "chat"),
        a2a_output_mode=getattr(flow, "a2a_output_mode", "text"),
    )
