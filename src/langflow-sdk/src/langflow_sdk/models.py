"""Pydantic models mirroring the Langflow REST API request/response shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Flow models
# ---------------------------------------------------------------------------


class FlowCreate(BaseModel):
    """Payload for creating a new flow."""

    name: str
    description: str | None = None
    data: dict[str, Any] | None = None
    is_component: bool = False
    endpoint_name: str | None = None
    tags: list[str] | None = None
    folder_id: UUID | None = None
    icon: str | None = None
    icon_bg_color: str | None = None
    locked: bool = False
    mcp_enabled: bool = False


class FlowUpdate(BaseModel):
    """Payload for partially updating a flow (all fields optional)."""

    name: str | None = None
    description: str | None = None
    data: dict[str, Any] | None = None
    endpoint_name: str | None = None
    tags: list[str] | None = None
    folder_id: UUID | None = None
    icon: str | None = None
    icon_bg_color: str | None = None
    locked: bool | None = None
    mcp_enabled: bool | None = None


class Flow(BaseModel):
    """A flow returned by the Langflow API."""

    id: UUID
    name: str
    description: str | None = None
    data: dict[str, Any] | None = None
    is_component: bool = False
    updated_at: datetime | None = None
    endpoint_name: str | None = None
    tags: list[str] | None = None
    folder_id: UUID | None = None
    user_id: UUID | None = None
    icon: str | None = None
    icon_bg_color: str | None = None
    locked: bool = False
    mcp_enabled: bool = False
    webhook: bool = False
    access_type: str = "PRIVATE"


# ---------------------------------------------------------------------------
# Project (Folder) models
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    """Payload for creating a new project (folder)."""

    name: str
    description: str | None = None
    flows_list: list[UUID] | None = None
    components_list: list[UUID] | None = None


class ProjectUpdate(BaseModel):
    """Payload for updating a project."""

    name: str | None = None
    description: str | None = None


class Project(BaseModel):
    """A project (folder) returned by the Langflow API."""

    id: UUID
    name: str
    description: str | None = None
    parent_id: UUID | None = None


class ProjectWithFlows(Project):
    """A project with its flows included."""

    flows: list[Flow] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Run models
# ---------------------------------------------------------------------------


class RunInput(BaseModel):
    """A single named input for a flow run."""

    components: list[str] = Field(default_factory=list)
    input_value: str = ""
    type: str = "chat"


class RunRequest(BaseModel):
    """Payload for running a flow via the API."""

    input_value: str = ""
    input_type: str = "chat"
    output_type: str = "chat"
    tweaks: dict[str, Any] | None = None
    stream: bool = False


class RunOutput(BaseModel):
    """A single output from a flow run."""

    results: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    outputs: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None
    timedelta: float | None = None


class RunResponse(BaseModel):
    """The full response from a flow run."""

    session_id: str | None = None
    outputs: list[RunOutput] = Field(default_factory=list)
