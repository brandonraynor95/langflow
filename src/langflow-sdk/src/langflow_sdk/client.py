"""Sync and async HTTP clients for the Langflow REST API."""

from __future__ import annotations

import io
import zipfile
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Self

import httpx

from langflow_sdk.exceptions import (
    LangflowAuthError,
    LangflowConnectionError,
    LangflowHTTPError,
    LangflowNotFoundError,
    LangflowValidationError,
)
from langflow_sdk.models import (
    Flow,
    FlowCreate,
    FlowUpdate,
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectWithFlows,
    RunRequest,
    RunResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

_DEFAULT_TIMEOUT = 60.0
_HTTP_201_CREATED = HTTPStatus.CREATED.value


def _raise_for_status(response: httpx.Response) -> None:
    """Convert httpx HTTP errors into typed SDK exceptions."""
    if response.is_success:
        return
    try:
        detail = response.json().get("detail", response.text)
    except Exception:  # noqa: BLE001
        detail = response.text

    status = response.status_code
    if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        raise LangflowAuthError(status, detail)
    if status == HTTPStatus.NOT_FOUND:
        raise LangflowNotFoundError(status, detail)
    if status == HTTPStatus.UNPROCESSABLE_ENTITY:
        raise LangflowValidationError(status, detail)
    raise LangflowHTTPError(status, detail)


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _connection_error(base_url: str, exc: Exception) -> LangflowConnectionError:
    msg = f"Could not connect to Langflow at {base_url}: {exc}"
    return LangflowConnectionError(msg)


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------


class LangflowClient:
    """Synchronous client for the Langflow REST API.

    Example::

        client = LangflowClient(
            base_url="https://langflow.example.com",
            api_key="<your-api-key>",  # pragma: allowlist secret
        )
        flows = client.list_flows()
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._owns_client = httpx_client is None
        self._http = httpx_client or httpx.Client(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = self._http.request(
                method,
                path,
                json=json,
                params=params,
                content=content,
                headers=headers,
            )
        except httpx.ConnectError as exc:
            raise _connection_error(self._base_url, exc) from exc
        _raise_for_status(response)
        return response

    # ------------------------------------------------------------------
    # Flows
    # ------------------------------------------------------------------

    def list_flows(
        self,
        *,
        folder_id: UUID | str | None = None,
        remove_example_flows: bool = False,
        components_only: bool = False,
        get_all: bool = False,
        header_flows: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> list[Flow]:
        params: dict[str, Any] = {
            "remove_example_flows": remove_example_flows,
            "components_only": components_only,
            "get_all": get_all,
            "header_flows": header_flows,
            "page": page,
            "size": size,
        }
        if folder_id is not None:
            params["folder_id"] = str(folder_id)
        resp = self._request("GET", "/api/v1/flows/", params=params)
        return [Flow.model_validate(f) for f in resp.json()]

    def get_flow(self, flow_id: UUID | str) -> Flow:
        resp = self._request("GET", f"/api/v1/flows/{flow_id}")
        return Flow.model_validate(resp.json())

    def create_flow(self, flow: FlowCreate) -> Flow:
        resp = self._request("POST", "/api/v1/flows/", json=flow.model_dump(exclude_none=True))
        return Flow.model_validate(resp.json())

    def update_flow(self, flow_id: UUID | str, update: FlowUpdate) -> Flow:
        resp = self._request(
            "PATCH",
            f"/api/v1/flows/{flow_id}",
            json=update.model_dump(exclude_none=True),
        )
        return Flow.model_validate(resp.json())

    def upsert_flow(self, flow_id: UUID | str, flow: FlowCreate) -> tuple[Flow, bool]:
        """Create-or-update a flow by its stable ID.

        Returns ``(flow, created)`` where ``created`` is ``True`` when a new
        flow was inserted and ``False`` when an existing one was updated.
        """
        resp = self._request(
            "PUT",
            f"/api/v1/flows/{flow_id}",
            json=flow.model_dump(exclude_none=True),
        )
        return Flow.model_validate(resp.json()), resp.status_code == _HTTP_201_CREATED

    def delete_flow(self, flow_id: UUID | str) -> None:
        self._request("DELETE", f"/api/v1/flows/{flow_id}")

    def run_flow(
        self,
        flow_id_or_endpoint: UUID | str,
        request: RunRequest,
    ) -> RunResponse:
        resp = self._request(
            "POST",
            f"/api/v1/run/{flow_id_or_endpoint}",
            json=request.model_dump(exclude_none=True),
        )
        return RunResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Projects (Folders)
    # ------------------------------------------------------------------

    def list_projects(self) -> list[Project]:
        resp = self._request("GET", "/api/v1/projects/")
        return [Project.model_validate(p) for p in resp.json()]

    def get_project(self, project_id: UUID | str) -> ProjectWithFlows:
        resp = self._request("GET", f"/api/v1/projects/{project_id}")
        return ProjectWithFlows.model_validate(resp.json())

    def create_project(self, project: ProjectCreate) -> Project:
        resp = self._request("POST", "/api/v1/projects/", json=project.model_dump(exclude_none=True))
        return Project.model_validate(resp.json())

    def update_project(self, project_id: UUID | str, update: ProjectUpdate) -> Project:
        resp = self._request(
            "PATCH",
            f"/api/v1/projects/{project_id}",
            json=update.model_dump(exclude_none=True),
        )
        return Project.model_validate(resp.json())

    def delete_project(self, project_id: UUID | str) -> None:
        self._request("DELETE", f"/api/v1/projects/{project_id}")

    def download_project(self, project_id: UUID | str) -> dict[str, bytes]:
        """Download all flows in a project.

        Returns a mapping of ``{flow_name: raw_json_bytes}`` extracted from
        the ZIP archive returned by the server.
        """
        resp = self._request("GET", f"/api/v1/projects/download/{project_id}")
        flows: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                flows[name] = zf.read(name)
        return flows

    def upload_project(self, zip_bytes: bytes) -> list[Flow]:
        """Upload a project ZIP archive and return the created flows."""
        resp = self._request(
            "POST",
            "/api/v1/projects/upload/",
            content=zip_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        return [Flow.model_validate(f) for f in resp.json()]


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class AsyncLangflowClient:
    """Async client for the Langflow REST API.

    Example::

        async with AsyncLangflowClient(
            base_url="https://langflow.example.com",
            api_key="<your-api-key>",  # pragma: allowlist secret
        ) as client:
            flows = await client.list_flows()
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._owns_client = httpx_client is None
        self._http = httpx_client or httpx.AsyncClient(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = await self._http.request(
                method,
                path,
                json=json,
                params=params,
                content=content,
                headers=headers,
            )
        except httpx.ConnectError as exc:
            raise _connection_error(self._base_url, exc) from exc
        _raise_for_status(response)
        return response

    # ------------------------------------------------------------------
    # Flows
    # ------------------------------------------------------------------

    async def list_flows(
        self,
        *,
        folder_id: UUID | str | None = None,
        remove_example_flows: bool = False,
        components_only: bool = False,
        get_all: bool = False,
        header_flows: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> list[Flow]:
        params: dict[str, Any] = {
            "remove_example_flows": remove_example_flows,
            "components_only": components_only,
            "get_all": get_all,
            "header_flows": header_flows,
            "page": page,
            "size": size,
        }
        if folder_id is not None:
            params["folder_id"] = str(folder_id)
        resp = await self._request("GET", "/api/v1/flows/", params=params)
        return [Flow.model_validate(f) for f in resp.json()]

    async def get_flow(self, flow_id: UUID | str) -> Flow:
        resp = await self._request("GET", f"/api/v1/flows/{flow_id}")
        return Flow.model_validate(resp.json())

    async def create_flow(self, flow: FlowCreate) -> Flow:
        resp = await self._request("POST", "/api/v1/flows/", json=flow.model_dump(exclude_none=True))
        return Flow.model_validate(resp.json())

    async def update_flow(self, flow_id: UUID | str, update: FlowUpdate) -> Flow:
        resp = await self._request(
            "PATCH",
            f"/api/v1/flows/{flow_id}",
            json=update.model_dump(exclude_none=True),
        )
        return Flow.model_validate(resp.json())

    async def upsert_flow(self, flow_id: UUID | str, flow: FlowCreate) -> tuple[Flow, bool]:
        """Create-or-update by stable ID. Returns ``(flow, created)``."""
        resp = await self._request(
            "PUT",
            f"/api/v1/flows/{flow_id}",
            json=flow.model_dump(exclude_none=True),
        )
        return Flow.model_validate(resp.json()), resp.status_code == _HTTP_201_CREATED

    async def delete_flow(self, flow_id: UUID | str) -> None:
        await self._request("DELETE", f"/api/v1/flows/{flow_id}")

    async def run_flow(
        self,
        flow_id_or_endpoint: UUID | str,
        request: RunRequest,
    ) -> RunResponse:
        resp = await self._request(
            "POST",
            f"/api/v1/run/{flow_id_or_endpoint}",
            json=request.model_dump(exclude_none=True),
        )
        return RunResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def list_projects(self) -> list[Project]:
        resp = await self._request("GET", "/api/v1/projects/")
        return [Project.model_validate(p) for p in resp.json()]

    async def get_project(self, project_id: UUID | str) -> ProjectWithFlows:
        resp = await self._request("GET", f"/api/v1/projects/{project_id}")
        return ProjectWithFlows.model_validate(resp.json())

    async def create_project(self, project: ProjectCreate) -> Project:
        resp = await self._request("POST", "/api/v1/projects/", json=project.model_dump(exclude_none=True))
        return Project.model_validate(resp.json())

    async def update_project(self, project_id: UUID | str, update: ProjectUpdate) -> Project:
        resp = await self._request(
            "PATCH",
            f"/api/v1/projects/{project_id}",
            json=update.model_dump(exclude_none=True),
        )
        return Project.model_validate(resp.json())

    async def delete_project(self, project_id: UUID | str) -> None:
        await self._request("DELETE", f"/api/v1/projects/{project_id}")

    async def download_project(self, project_id: UUID | str) -> dict[str, bytes]:
        resp = await self._request("GET", f"/api/v1/projects/download/{project_id}")
        flows: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                flows[name] = zf.read(name)
        return flows

    async def upload_project(self, zip_bytes: bytes) -> list[Flow]:
        resp = await self._request(
            "POST",
            "/api/v1/projects/upload/",
            content=zip_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        return [Flow.model_validate(f) for f in resp.json()]
