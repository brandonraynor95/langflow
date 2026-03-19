"""lfx push -- push normalized flow JSON to a remote Langflow instance.

Uses stable flow IDs for upsert (PUT /api/v1/flows/{id}), so repeated pushes
are idempotent: the first push creates the flow, subsequent ones update it in
place without changing its ID on the remote instance.

Usage examples
--------------
Push a single flow to staging::

    lfx push my_flow.json --env staging

Push several flows at once::

    lfx push flows/*.json --env staging

Push all flows in a directory and place them in a named project::

    lfx push --dir ./flows/ --env staging --project "My RAG Pipeline"

Dry-run to see what would happen::

    lfx push ./flows/ --env production --dry-run
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

console = Console(stderr=True)
ok_console = Console()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class PushResult:
    path: Path
    flow_id: UUID
    flow_name: str
    status: str  # "created" | "updated" | "error" | "dry-run"
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("created", "updated", "dry-run")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sdk() -> Any:
    """Lazy import to keep startup fast."""
    try:
        import langflow_sdk  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = "langflow-sdk is required for lfx push. Install it with: pip install langflow-sdk"
        raise typer.BadParameter(msg) from exc
    else:
        return langflow_sdk


def _load_flow_file(path: Path) -> dict[str, Any]:
    """Read and parse a flow JSON file; raise Exit on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]Error:[/red] Cannot read {path}: {exc}")
        raise typer.Exit(1) from exc


def _extract_flow_id(flow: dict[str, Any], path: Path) -> UUID:
    """Extract and validate the flow's stable ID from the JSON."""
    raw_id = flow.get("id")
    if not raw_id:
        console.print(f"[red]Error:[/red] {path} has no 'id' field. Run [bold]lfx export[/bold] first.")
        raise typer.Exit(1)
    try:
        return UUID(str(raw_id))
    except ValueError:
        console.print(f"[red]Error:[/red] {path} has an invalid 'id': {raw_id!r}")
        raise typer.Exit(1)  # noqa: B904


def _flow_to_create(sdk: Any, flow: dict[str, Any], folder_id: UUID | None) -> Any:
    """Build a FlowCreate from a normalized flow dict."""
    return sdk.FlowCreate(
        name=flow.get("name", "Untitled"),
        description=flow.get("description"),
        data=flow.get("data"),
        is_component=flow.get("is_component", False),
        endpoint_name=flow.get("endpoint_name"),
        tags=flow.get("tags"),
        folder_id=folder_id or (UUID(flow["folder_id"]) if flow.get("folder_id") else None),
        icon=flow.get("icon"),
        icon_bg_color=flow.get("icon_bg_color"),
        locked=flow.get("locked", False),
        mcp_enabled=flow.get("mcp_enabled", False),
    )


def _upsert_single(
    client: Any,
    sdk: Any,
    path: Path,
    flow_id: UUID,
    flow_create: Any,
    *,
    dry_run: bool,
    flow_name: str,
) -> PushResult:
    if dry_run:
        return PushResult(path=path, flow_id=flow_id, flow_name=flow_name, status="dry-run")

    try:
        _, created = client.upsert_flow(flow_id, flow_create)
        status = "created" if created else "updated"
        return PushResult(path=path, flow_id=flow_id, flow_name=flow_name, status=status)
    except sdk.LangflowHTTPError as exc:
        return PushResult(
            path=path,
            flow_id=flow_id,
            flow_name=flow_name,
            status="error",
            error=str(exc),
        )


def _find_or_create_project(
    client: Any,
    sdk: Any,
    project_name: str,
    *,
    dry_run: bool,
) -> UUID | None:
    """Return the UUID of a project with *project_name*, creating if needed.

    Returns ``None`` in dry-run mode (project may not exist yet).
    """
    projects = client.list_projects()
    for p in projects:
        if p.name == project_name:
            console.print(f"[dim]Project[/dim] {project_name!r} found (id={p.id})")
            return p.id

    if dry_run:
        console.print(f"[dim]Project[/dim] {project_name!r} would be created (dry-run)")
        return None

    project = client.create_project(sdk.ProjectCreate(name=project_name))
    console.print(f"[green]Created project[/green] {project_name!r} (id={project.id})")
    return project.id


def _collect_flow_files(sources: list[str], dir_path: str | None) -> list[Path]:
    """Resolve the set of flow JSON files to push."""
    paths: list[Path] = []

    if dir_path:
        d = Path(dir_path)
        if not d.is_dir():
            console.print(f"[red]Error:[/red] --dir {d} is not a directory.")
            raise typer.Exit(1)
        paths.extend(sorted(d.glob("*.json")))
        if not paths:
            console.print(f"[yellow]Warning:[/yellow] No *.json files found in {d}")

    for s in sources:
        p = Path(s)
        if not p.exists():
            console.print(f"[red]Error:[/red] File not found: {p}")
            raise typer.Exit(1)
        paths.append(p)

    return paths


def _render_results(results: list[PushResult], *, dry_run: bool) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("File")
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Status")

    status_colors = {
        "created": "green",
        "updated": "cyan",
        "dry-run": "yellow",
        "error": "red",
    }

    for r in results:
        color = status_colors.get(r.status, "white")
        label = r.status.upper() + (f": {r.error}" if r.error else "")
        table.add_row(
            str(r.path),
            r.flow_name,
            str(r.flow_id),
            f"[{color}]{label}[/{color}]",
        )

    ok_console.print()
    ok_console.print(table)

    errors = [r for r in results if not r.ok]
    if errors:
        console.print(f"\n[red]{len(errors)} push(es) failed.[/red]")
    elif dry_run:
        ok_console.print(f"\n[yellow]{len(results)} flow(s) would be pushed (dry-run).[/yellow]")
    else:
        created = sum(1 for r in results if r.status == "created")
        updated = sum(1 for r in results if r.status == "updated")
        ok_console.print(f"\n[green]{created} created, {updated} updated.[/green]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def push_command(
    flow_paths: list[str],
    *,
    env: str | None,
    dir_path: str | None,
    project: str | None,
    project_id: str | None,
    environments_file: str | None,
    target: str | None = None,
    api_key: str | None = None,
    dry_run: bool,
    normalize: bool,
    strip_secrets: bool,
) -> None:
    sdk = _load_sdk()

    from lfx.config import ConfigError, resolve_environment

    try:
        env_cfg = resolve_environment(
            env,
            target=target,
            api_key=api_key,
            environments_file=environments_file,
        )
    except ConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    client = sdk.Client(base_url=env_cfg.url, api_key=env_cfg.api_key)

    paths = _collect_flow_files(flow_paths, dir_path)
    if not paths:
        console.print("[red]Error:[/red] No flow files to push.")
        raise typer.Exit(1)

    # Resolve target project folder_id
    target_folder_id: UUID | None = None
    if project_id:
        target_folder_id = UUID(project_id)
    elif project:
        target_folder_id = _find_or_create_project(client, sdk, project, dry_run=dry_run)

    results: list[PushResult] = []

    for path in paths:
        raw_flow = _load_flow_file(path)

        if normalize:
            raw_flow = sdk.normalize_flow(
                raw_flow,
                strip_volatile=True,
                strip_secrets=strip_secrets,
                sort_keys=True,
            )

        flow_id = _extract_flow_id(raw_flow, path)
        flow_name = raw_flow.get("name", path.stem)
        flow_create = _flow_to_create(sdk, raw_flow, target_folder_id)

        result = _upsert_single(
            client,
            sdk,
            path,
            flow_id,
            flow_create,
            dry_run=dry_run,
            flow_name=flow_name,
        )
        results.append(result)

        if dry_run:
            console.print(f"[yellow]DRY-RUN[/yellow] Would push {flow_name!r} ({flow_id})")
        elif result.ok:
            action = "Created" if result.status == "created" else "Updated"
            console.print(f"[green]{action}[/green] {flow_name!r} ({flow_id})")
        else:
            console.print(f"[red]Failed[/red]  {flow_name!r} ({flow_id}): {result.error}")

    _render_results(results, dry_run=dry_run)

    if any(not r.ok for r in results):
        raise typer.Exit(1)
