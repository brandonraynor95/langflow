"""Sync and async HTTP clients for the Langflow REST API.

Preferred usage via the short aliases::

    from langflow_sdk import Client, AsyncClient

    client = Client("https://langflow.example.com", api_key="...")
    flows  = client.list_flows()
    result = client.run_flow("my-endpoint", RunRequest(input_value="Hello"))
"""

from __future__ import annotations

import io
import json
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
    StreamChunk,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from uuid import UUID

_DEFAULT_TIMEOUT = 60.0
_HTTP_201_CREATED = HTTPStatus.CREATED.value


def _raise_for_status_code(status: int, detail: str) -> None:
    """Raise a typed SDK exception for the given HTTP status code and detail."""
    if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        raise LangflowAuthError(status, detail)
    if status == HTTPStatus.NOT_FOUND:
        raise LangflowNotFoundError(status, detail)
    if status == HTTPStatus.UNPROCESSABLE_ENTITY:
        raise LangflowValidationError(status, detail)
    raise LangflowHTTPError(status, detail)


def _raise_for_status(response: httpx.Response) -> None:
    """Convert httpx HTTP errors into typed SDK exceptions."""
    if response.is_success:
        return
    try:
        detail = response.json().get("detail", response.text)
    except Exception:  # noqa: BLE001
        detail = response.text
    _raise_for_status_code(response.status_code, detail)


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

    Prefer the short alias :data:`Client` for new code::

        from langflow_sdk import Client

        client = Client("https://langflow.example.com", api_key="...")
        flows  = client.list_flows()
        result = client.run_flow("my-endpoint", RunRequest(input_value="Hello"))
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
        resp = self._request("POST", "/api/v1/flows/", json=flow.model_dump(mode="json", exclude_none=True))
        return Flow.model_validate(resp.json())

    def update_flow(self, flow_id: UUID | str, update: FlowUpdate) -> Flow:
        resp = self._request(
            "PATCH",
            f"/api/v1/flows/{flow_id}",
            json=update.model_dump(mode="json", exclude_none=True),
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
            json=flow.model_dump(mode="json", exclude_none=True),
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
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return RunResponse.model_validate(resp.json())

    def run(
        self,
        flow_id_or_endpoint: UUID | str,
        input_value: str = "",
        *,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
    ) -> RunResponse:
        """Run a flow and return the full response.

        Convenience wrapper around :meth:`run_flow` that accepts plain keyword
        arguments instead of a :class:`RunRequest`::

            result = client.run("my-flow", input_value="Hello")
            print(result.first_text_output())
        """
        return self.run_flow(
            flow_id_or_endpoint,
            RunRequest(
                input_value=input_value,
                input_type=input_type,
                output_type=output_type,
                tweaks=tweaks,
            ),
        )

    def stream(
        self,
        flow_id_or_endpoint: UUID | str,
        input_value: str = "",
        *,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
    ) -> Iterator[StreamChunk]:
        """Stream a flow run, yielding :class:`StreamChunk` objects as they arrive.

        Uses server-sent events (SSE) to receive incremental output::

            for chunk in client.stream("my-flow", input_value="Hello"):
                if chunk.is_token:
                    print(chunk.text, end="", flush=True)
                elif chunk.is_end:
                    response = chunk.final_response()
        """
        payload = RunRequest(
            input_value=input_value,
            input_type=input_type,
            output_type=output_type,
            tweaks=tweaks,
            stream=True,
        ).model_dump(mode="json", exclude_none=True)
        return self._iter_stream(f"/api/v1/run/{flow_id_or_endpoint}", payload)

    def _iter_stream(self, path: str, payload: dict[str, Any]) -> Iterator[StreamChunk]:
        """Open a streaming POST request and yield parsed event chunks."""
        try:
            with self._http.stream("POST", path, json=payload) as response:
                if not response.is_success:
                    body = response.read()
                    try:
                        parsed = json.loads(body)
                        detail = (
                            parsed.get("detail", body.decode(errors="replace"))
                            if isinstance(parsed, dict)
                            else body.decode(errors="replace")
                        )
                    except Exception:  # noqa: BLE001
                        detail = body.decode(errors="replace")
                    _raise_for_status_code(response.status_code, detail)
                for line in response.iter_lines():
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                        yield StreamChunk(event=obj["event"], data=obj.get("data", {}))
                    except (json.JSONDecodeError, KeyError):
                        continue
        except httpx.ConnectError as exc:
            raise _connection_error(self._base_url, exc) from exc

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
        resp = self._request("POST", "/api/v1/projects/", json=project.model_dump(mode="json", exclude_none=True))
        return Project.model_validate(resp.json())

    def update_project(self, project_id: UUID | str, update: ProjectUpdate) -> Project:
        resp = self._request(
            "PATCH",
            f"/api/v1/projects/{project_id}",
            json=update.model_dump(mode="json", exclude_none=True),
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

    Prefer the short alias :data:`AsyncClient` for new code::

        from langflow_sdk import AsyncClient

        async with AsyncClient("https://langflow.example.com", api_key="...") as client:
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
        resp = await self._request("POST", "/api/v1/flows/", json=flow.model_dump(mode="json", exclude_none=True))
        return Flow.model_validate(resp.json())

    async def update_flow(self, flow_id: UUID | str, update: FlowUpdate) -> Flow:
        resp = await self._request(
            "PATCH",
            f"/api/v1/flows/{flow_id}",
            json=update.model_dump(mode="json", exclude_none=True),
        )
        return Flow.model_validate(resp.json())

    async def upsert_flow(self, flow_id: UUID | str, flow: FlowCreate) -> tuple[Flow, bool]:
        """Create-or-update by stable ID. Returns ``(flow, created)``."""
        resp = await self._request(
            "PUT",
            f"/api/v1/flows/{flow_id}",
            json=flow.model_dump(mode="json", exclude_none=True),
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
            json=request.model_dump(mode="json", exclude_none=True),
        )
        return RunResponse.model_validate(resp.json())

    async def run(
        self,
        flow_id_or_endpoint: UUID | str,
        input_value: str = "",
        *,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
    ) -> RunResponse:
        """Run a flow and return the full response.

        Convenience wrapper around :meth:`run_flow` that accepts plain keyword
        arguments instead of a :class:`RunRequest`::

            result = await client.run("my-flow", input_value="Hello")
            print(result.first_text_output())
        """
        return await self.run_flow(
            flow_id_or_endpoint,
            RunRequest(
                input_value=input_value,
                input_type=input_type,
                output_type=output_type,
                tweaks=tweaks,
            ),
        )

    def stream(
        self,
        flow_id_or_endpoint: UUID | str,
        input_value: str = "",
        *,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a flow run, yielding :class:`StreamChunk` objects as they arrive.

        Uses server-sent events (SSE) to receive incremental output::

            async for chunk in client.stream("my-flow", input_value="Hello"):
                if chunk.is_token:
                    print(chunk.text, end="", flush=True)
                elif chunk.is_end:
                    response = chunk.final_response()
        """
        payload = RunRequest(
            input_value=input_value,
            input_type=input_type,
            output_type=output_type,
            tweaks=tweaks,
            stream=True,
        ).model_dump(mode="json", exclude_none=True)
        return self._aiter_stream(f"/api/v1/run/{flow_id_or_endpoint}", payload)

    async def _aiter_stream(self, path: str, payload: dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """Open a streaming POST request and async-yield parsed event chunks."""
        try:
            async with self._http.stream("POST", path, json=payload) as response:
                if not response.is_success:
                    body = await response.aread()
                    try:
                        parsed = json.loads(body)
                        detail = (
                            parsed.get("detail", body.decode(errors="replace"))
                            if isinstance(parsed, dict)
                            else body.decode(errors="replace")
                        )
                    except Exception:  # noqa: BLE001
                        detail = body.decode(errors="replace")
                    _raise_for_status_code(response.status_code, detail)
                async for line in response.aiter_lines():
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                        yield StreamChunk(event=obj["event"], data=obj.get("data", {}))
                    except (json.JSONDecodeError, KeyError):
                        continue
        except httpx.ConnectError as exc:
            raise _connection_error(self._base_url, exc) from exc

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
        resp = await self._request("POST", "/api/v1/projects/", json=project.model_dump(mode="json", exclude_none=True))
        return Project.model_validate(resp.json())

    async def update_project(self, project_id: UUID | str, update: ProjectUpdate) -> Project:
        resp = await self._request(
            "PATCH",
            f"/api/v1/projects/{project_id}",
            json=update.model_dump(mode="json", exclude_none=True),
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


# ---------------------------------------------------------------------------
# Short aliases  (preferred for new code)
# ---------------------------------------------------------------------------

#: Short alias for :class:`LangflowClient`.
#:
#: Example::
#:
#:     from langflow_sdk import Client
#:     client = Client("https://langflow.example.com", api_key="...")
#:     flows  = client.list_flows()
#:     result = client.run_flow("my-endpoint", RunRequest(input_value="Hello"))
Client = LangflowClient

#: Short alias for :class:`AsyncLangflowClient`.
#:
#: Example::
#:
#:     from langflow_sdk import AsyncClient
#:     async with AsyncClient("https://langflow.example.com", api_key="...") as c:
#:         flows = await c.list_flows()
AsyncClient = AsyncLangflowClient
