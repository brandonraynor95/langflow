"""FastAPI router for A2A protocol endpoints.

Two routers are defined:
1. `a2a_router` — Public A2A protocol endpoints mounted at /a2a/{agent_slug}/
2. `a2a_config_router` — Internal admin endpoints for managing A2A config

The instance-level toggle LANGFLOW_A2A_ENABLED controls whether the public
A2A endpoints are active. When disabled, all public routes return 404.
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select

from langflow.api.a2a.agent_card import generate_agent_card
from langflow.api.a2a.config import validate_a2a_slug, validate_flow_eligible_for_a2a
from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.flow.model import Flow

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
