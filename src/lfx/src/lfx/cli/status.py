"""lfx status -- compare local flow files against a remote Langflow instance.

Shows, for each local flow JSON, whether it is in sync with the remote,
ahead (locally modified), brand new (not yet pushed), or missing entirely.
Optionally surfaces flows that exist on the server but have no local file.

Examples::

    lfx status                          # scans flows/ in cwd, uses [defaults] env
    lfx status --env staging            # compare against staging
    lfx status --dir ./my-flows/        # specify a custom flows directory
    lfx status --env prod --remote-only # also show server flows not tracked locally
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import typer
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

_STATUS_SYNCED = "synced"
_STATUS_AHEAD = "ahead"
_STATUS_NEW = "new"
_STATUS_REMOTE_ONLY = "remote-only"
_STATUS_NO_ID = "no-id"
_STATUS_ERROR = "error"

_STATUS_STYLE: dict[str, tuple[str, str, str]] = {
    _STATUS_SYNCED: ("✓", "green", "synced"),
    _STATUS_AHEAD: ("↑", "yellow", "ahead"),
    _STATUS_NEW: ("+", "cyan", "new"),
    _STATUS_REMOTE_ONLY: ("↓", "blue", "remote only"),
    _STATUS_NO_ID: ("?", "dim", "no id"),
    _STATUS_ERROR: ("✗", "red", "error"),
}


@dataclass
class FlowStatus:
    name: str
    status: str
    path: Path | None = None
    flow_id: UUID | None = None
    detail: str = field(default="")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sdk() -> tuple[object, object, object]:
    """Return (normalize_flow, flow_to_json, get_client) from langflow_sdk."""
    try:
        from langflow_sdk.environments import get_client
        from langflow_sdk.serialization import flow_to_json, normalize_flow
    except ImportError as exc:
        msg = "langflow-sdk is required for lfx status. Install with: pip install langflow-sdk"
        raise typer.BadParameter(msg) from exc
    else:
        return normalize_flow, flow_to_json, get_client


def _flow_hash(flow_dict: dict, normalize_flow: object, flow_to_json: object) -> str:
    """Return a short deterministic hash of the normalized flow content."""
    normalized = normalize_flow(flow_dict)  # type: ignore[operator]
    content = flow_to_json(normalized)  # type: ignore[operator]
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _collect_files(dir_path: str | None, flow_paths: list[str]) -> list[Path]:
    """Resolve the set of local flow files to examine."""
    files: list[Path] = []

    if dir_path:
        d = Path(dir_path)
        if not d.is_dir():
            msg = f"Directory not found: {d}"
            console.print(f"[red]Error:[/red] {msg}")
            raise typer.Exit(1)
        files.extend(sorted(d.glob("*.json")))
    elif flow_paths:
        files.extend(Path(p) for p in flow_paths)
    else:
        # Default: flows/ in cwd
        default = Path.cwd() / "flows"
        if default.is_dir():
            files.extend(sorted(default.glob("*.json")))

    return files


def _render_table(statuses: list[FlowStatus], env_label: str) -> None:
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold",
        title=f"Flow status vs [bold]{env_label}[/bold]",
        title_justify="left",
    )
    table.add_column("Flow", min_width=24)
    table.add_column("ID", style="dim", min_width=10)
    table.add_column("File", style="dim")
    table.add_column("Status", min_width=14)

    for s in statuses:
        icon, color, label = _STATUS_STYLE.get(s.status, ("?", "dim", s.status))
        detail_str = f"  [dim]({s.detail})[/dim]" if s.detail else ""
        id_str = str(s.flow_id)[:8] + "…" if s.flow_id else "—"
        file_str = s.path.name if s.path else "—"
        table.add_row(
            s.name,
            id_str,
            file_str,
            f"[{color}]{icon} {label}[/{color}]{detail_str}",
        )

    console.print(table)

    # Summary line
    counts: dict[str, int] = {}
    for s in statuses:
        counts[s.status] = counts.get(s.status, 0) + 1

    parts = []
    for status, (_, color, label) in _STATUS_STYLE.items():
        if counts.get(status):
            parts.append(f"[{color}]{counts[status]} {label}[/{color}]")

    if parts:
        console.print("  " + "  ·  ".join(parts))
        console.print()


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def status_command(
    dir_path: str | None,
    flow_paths: list[str],
    env: str | None,
    environments_file: str | None,
    *,
    show_remote_only: bool,
) -> None:
    """Compare local flow files against the remote instance and render a status table."""
    normalize_flow, flow_to_json, get_client = _load_sdk()
    from langflow_sdk.exceptions import LangflowNotFoundError

    env_file_path = Path(environments_file) if environments_file else None
    try:
        client = get_client(env, config_file=env_file_path)
    except Exception as exc:
        label = env or "default"
        console.print(f"[red]Error:[/red] Could not connect to environment {label!r}: {exc}")
        raise typer.Exit(1) from exc

    env_label = env or "default"
    local_files = _collect_files(dir_path, flow_paths)

    if not local_files and not show_remote_only:
        console.print("[yellow]No flow files found.[/yellow] Use [bold]--dir[/bold] to specify a directory.")
        raise typer.Exit(0)

    statuses: list[FlowStatus] = []
    seen_ids: set[UUID] = set()

    # ------------------------------------------------------------------ #
    # Check each local file                                               #
    # ------------------------------------------------------------------ #
    for path in local_files:
        if not path.exists():
            statuses.append(FlowStatus(name=path.name, status=_STATUS_ERROR, path=path, detail="file not found"))
            continue

        try:
            raw: dict = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            statuses.append(FlowStatus(name=path.name, status=_STATUS_ERROR, path=path, detail=str(exc)))
            continue

        name: str = raw.get("name", path.stem)
        raw_id = raw.get("id")

        if not raw_id:
            statuses.append(
                FlowStatus(
                    name=name,
                    status=_STATUS_NO_ID,
                    path=path,
                    detail="run lfx export --env <env> first to assign a stable id",
                )
            )
            continue

        try:
            flow_id = UUID(str(raw_id))
        except ValueError:
            statuses.append(FlowStatus(name=name, status=_STATUS_ERROR, path=path, detail=f"invalid id: {raw_id!r}"))
            continue

        seen_ids.add(flow_id)

        try:
            remote_flow = client.get_flow(flow_id)
        except LangflowNotFoundError:
            statuses.append(FlowStatus(name=name, status=_STATUS_NEW, path=path, flow_id=flow_id))
            continue
        except Exception as exc:  # noqa: BLE001
            statuses.append(FlowStatus(name=name, status=_STATUS_ERROR, path=path, flow_id=flow_id, detail=str(exc)))
            continue

        local_hash = _flow_hash(raw, normalize_flow, flow_to_json)
        remote_hash = _flow_hash(remote_flow.model_dump(mode="json"), normalize_flow, flow_to_json)

        if local_hash == remote_hash:
            statuses.append(FlowStatus(name=name, status=_STATUS_SYNCED, path=path, flow_id=flow_id))
        else:
            statuses.append(FlowStatus(name=name, status=_STATUS_AHEAD, path=path, flow_id=flow_id))

    # ------------------------------------------------------------------ #
    # Remote-only flows                                                   #
    # ------------------------------------------------------------------ #
    if show_remote_only:
        try:
            all_remote = client.list_flows(get_all=True)
            statuses.extend(
                FlowStatus(
                    name=remote_flow.name,
                    status=_STATUS_REMOTE_ONLY,
                    flow_id=remote_flow.id,
                )
                for remote_flow in all_remote
                if remote_flow.id not in seen_ids
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]Warning:[/yellow] Could not list remote flows: {exc}")

    _render_table(statuses, env_label)

    # Exit 1 when anything is out of sync so CI pipelines can detect drift
    not_clean = [s for s in statuses if s.status not in (_STATUS_SYNCED,)]
    if not_clean:
        raise typer.Exit(1)
