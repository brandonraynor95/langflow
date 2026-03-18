"""lfx validate — structural and semantic validation of Langflow flow JSON.

Validation levels (each level implies all levels below it):

    Level 1 – structural
        The file parses as valid JSON and contains the expected top-level keys
        (``id``, ``name``, ``data``, ``data.nodes``, ``data.edges``).

    Level 2 – components
        Every node's ``data.type`` references a component type that exists in
        the lfx component registry.

    Level 3 – edge types
        Connected ports carry compatible types (source output type must be
        assignable to target input type).

    Level 4 – required inputs
        Every required input field on every component has a value or an
        incoming edge connected to it.

Use ``--level`` to select how deep to go, or ``--skip-*`` flags to opt out of
individual checks while still running the others.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

console = Console(stderr=True)
ok_console = Console()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    level: int
    severity: str  # "error" | "warning"
    node_id: str | None
    node_name: str | None
    message: str


@dataclass
class ValidationResult:
    path: Path
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# Level 1 – structural checks (pure JSON, no component loading)
# ---------------------------------------------------------------------------

_REQUIRED_TOP_LEVEL = {"id", "name", "data"}
_REQUIRED_DATA_KEYS = {"nodes", "edges"}


def _check_structural(flow: dict[str, Any], result: ValidationResult) -> bool:
    """Return False if the flow is so broken that further checks cannot run."""
    ok = True
    missing_top = _REQUIRED_TOP_LEVEL - set(flow.keys())
    for key in sorted(missing_top):
        result.issues.append(
            ValidationIssue(
                level=1,
                severity="error",
                node_id=None,
                node_name=None,
                message=f"Missing required top-level field: '{key}'",
            )
        )
        ok = False

    data = flow.get("data")
    if not isinstance(data, dict):
        result.issues.append(
            ValidationIssue(
                level=1,
                severity="error",
                node_id=None,
                node_name=None,
                message="'data' must be a JSON object",
            )
        )
        return False

    missing_data = _REQUIRED_DATA_KEYS - set(data.keys())
    for key in sorted(missing_data):
        result.issues.append(
            ValidationIssue(
                level=1,
                severity="error",
                node_id=None,
                node_name=None,
                message=f"Missing required field: 'data.{key}'",
            )
        )
        ok = False

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        result.issues.append(
            ValidationIssue(
                level=1,
                severity="error",
                node_id=None,
                node_name=None,
                message="'data.nodes' must be a JSON array",
            )
        )
        return False

    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            result.issues.append(
                ValidationIssue(
                    level=1,
                    severity="error",
                    node_id=None,
                    node_name=None,
                    message=f"Node at index {i} is not a JSON object",
                )
            )
            ok = False
            continue
        for req in ("id", "data"):
            if req not in node:
                result.issues.append(
                    ValidationIssue(
                        level=1,
                        severity="error",
                        node_id=node.get("id"),
                        node_name=_node_display_name(node),
                        message=f"Node at index {i} is missing required field '{req}'",
                    )
                )
                ok = False

        node_data = node.get("data", {})
        if isinstance(node_data, dict) and "type" not in node_data:
            result.issues.append(
                ValidationIssue(
                    level=1,
                    severity="warning",
                    node_id=node.get("id"),
                    node_name=_node_display_name(node),
                    message="Node is missing 'data.type' — component type cannot be determined",
                )
            )

    return ok


def _node_display_name(node: dict[str, Any]) -> str | None:
    return (
        node.get("data", {}).get("node", {}).get("display_name")
        or node.get("data", {}).get("id")
        or node.get("id")
    )


# ---------------------------------------------------------------------------
# Level 2 – component existence (loads lfx component registry)
# ---------------------------------------------------------------------------


def _check_component_existence(
    flow: dict[str, Any], result: ValidationResult
) -> None:
    try:
        from lfx.interface.utils import initialize_components  # type: ignore[import-untyped]

        component_registry: set[str] = set(initialize_components().keys())
    except Exception as exc:  # noqa: BLE001
        result.issues.append(
            ValidationIssue(
                level=2,
                severity="warning",
                node_id=None,
                node_name=None,
                message=f"Could not load component registry (skipping component checks): {exc}",
            )
        )
        return

    for node in flow.get("data", {}).get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_data = node.get("data", {})
        component_type: str | None = node_data.get("type")
        if not component_type:
            continue
        if component_type not in component_registry:
            result.issues.append(
                ValidationIssue(
                    level=2,
                    severity="error",
                    node_id=node.get("id"),
                    node_name=_node_display_name(node),
                    message=(
                        f"Unknown component type '{component_type}'. "
                        "This component may be missing or outdated."
                    ),
                )
            )


# ---------------------------------------------------------------------------
# Level 3 – edge type compatibility
# ---------------------------------------------------------------------------


def _check_edge_type_compatibility(
    flow: dict[str, Any], result: ValidationResult
) -> None:
    """Check that source output types are compatible with target input types.

    This is a best-effort check: if type information is missing from the node
    template we emit a warning rather than an error.
    """
    data = flow.get("data", {})
    nodes_by_id: dict[str, dict[str, Any]] = {
        n["id"]: n for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n
    }

    for edge in data.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src_id: str | None = edge.get("source")
        tgt_id: str | None = edge.get("target")
        src_handle: dict[str, Any] = edge.get("data", {}).get("sourceHandle", {}) or {}
        tgt_handle: dict[str, Any] = edge.get("data", {}).get("targetHandle", {}) or {}

        if not src_id or not tgt_id:
            continue

        src_node = nodes_by_id.get(src_id)
        tgt_node = nodes_by_id.get(tgt_id)
        if not src_node or not tgt_node:
            result.issues.append(
                ValidationIssue(
                    level=3,
                    severity="error",
                    node_id=None,
                    node_name=None,
                    message=(
                        f"Edge references non-existent node(s): "
                        f"source={src_id!r}, target={tgt_id!r}"
                    ),
                )
            )
            continue

        src_type: str | None = src_handle.get("output_types", [None])[0] if src_handle.get("output_types") else None
        tgt_type: str | None = tgt_handle.get("type")

        if src_type and tgt_type and src_type != tgt_type and tgt_type != "Any":
            result.issues.append(
                ValidationIssue(
                    level=3,
                    severity="warning",
                    node_id=tgt_id,
                    node_name=_node_display_name(tgt_node),
                    message=(
                        f"Possible type mismatch on edge from "
                        f"'{_node_display_name(src_node)}' → '{_node_display_name(tgt_node)}': "
                        f"source emits '{src_type}', target expects '{tgt_type}'"
                    ),
                )
            )


# ---------------------------------------------------------------------------
# Level 4 – required inputs connected
# ---------------------------------------------------------------------------


def _check_required_inputs(
    flow: dict[str, Any], result: ValidationResult
) -> None:
    """Verify that all required input fields have a value or an incoming edge."""
    data = flow.get("data", {})
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # Build set of (node_id, field_name) pairs that receive an edge
    connected_inputs: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        tgt_id = edge.get("target")
        tgt_handle = edge.get("data", {}).get("targetHandle", {}) or {}
        field_name = tgt_handle.get("fieldName")
        if tgt_id and field_name:
            connected_inputs.add((tgt_id, field_name))

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_data = node.get("data", {})
        template: dict[str, Any] = node_data.get("node", {}).get("template", {})

        for field_name, field_def in template.items():
            if field_name.startswith("_") or not isinstance(field_def, dict):
                continue
            is_required = field_def.get("required", False)
            show = field_def.get("show", True)
            if not is_required or not show:
                continue

            has_value = field_def.get("value") not in (None, "", [], {})
            has_edge = (node_id, field_name) in connected_inputs

            if not has_value and not has_edge:
                result.issues.append(
                    ValidationIssue(
                        level=4,
                        severity="error",
                        node_id=node_id,
                        node_name=_node_display_name(node),
                        message=(
                            f"Required input '{field_name}' has no value and no incoming edge"
                        ),
                    )
                )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_flow_file(
    path: Path,
    *,
    level: int = 4,
    skip_components: bool = False,
    skip_edge_types: bool = False,
    skip_required_inputs: bool = False,
) -> ValidationResult:
    result = ValidationResult(path=path)

    try:
        raw = path.read_text(encoding="utf-8")
        flow: dict[str, Any] = json.loads(raw)
    except (OSError, PermissionError) as exc:
        result.issues.append(
            ValidationIssue(
                level=1, severity="error", node_id=None, node_name=None,
                message=f"Cannot read file: {exc}",
            )
        )
        return result
    except json.JSONDecodeError as exc:
        result.issues.append(
            ValidationIssue(
                level=1, severity="error", node_id=None, node_name=None,
                message=f"Invalid JSON: {exc}",
            )
        )
        return result

    # Level 1 – structural
    can_continue = _check_structural(flow, result)
    if not can_continue or level < 2:
        return result

    # Level 2 – component existence
    if not skip_components:
        _check_component_existence(flow, result)
    if level < 3:
        return result

    # Level 3 – edge type compatibility
    if not skip_edge_types:
        _check_edge_type_compatibility(flow, result)
    if level < 4:
        return result

    # Level 4 – required inputs
    if not skip_required_inputs:
        _check_required_inputs(flow, result)

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _render_results(results: list[ValidationResult], *, verbose: bool) -> None:
    for result in results:
        label = f"[bold]{result.path}[/bold]"
        if result.ok:
            ok_console.print(f"[green]✓[/green] {label}")
        else:
            console.print(f"[red]✗[/red] {label}")

        if verbose or not result.ok:
            for issue in result.issues:
                color = "red" if issue.severity == "error" else "yellow"
                loc = f" [{issue.node_name or issue.node_id}]" if (issue.node_id or issue.node_name) else ""
                console.print(
                    f"  [{color}][L{issue.level} {issue.severity.upper()}][/{color}]{loc} {issue.message}"
                )


def validate_command(
    flow_paths: list[str],
    level: int,
    skip_components: bool,
    skip_edge_types: bool,
    skip_required_inputs: bool,
    verbose: bool,
    output_format: str,
) -> None:
    paths: list[Path] = []
    for raw in flow_paths:
        p = Path(raw)
        if not p.exists():
            console.print(f"[red]Error:[/red] File not found: {p}")
            raise typer.Exit(2)
        paths.append(p)

    results = [
        validate_flow_file(
            p,
            level=level,
            skip_components=skip_components,
            skip_edge_types=skip_edge_types,
            skip_required_inputs=skip_required_inputs,
        )
        for p in paths
    ]

    if output_format == "json":
        import json as _json

        out = []
        for r in results:
            out.append({
                "path": str(r.path),
                "ok": r.ok,
                "issues": [
                    {
                        "level": i.level,
                        "severity": i.severity,
                        "node_id": i.node_id,
                        "node_name": i.node_name,
                        "message": i.message,
                    }
                    for i in r.issues
                ],
            })
        sys.stdout.write(_json.dumps(out, indent=2) + "\n")
    else:
        _render_results(results, verbose=verbose)

    if any(not r.ok for r in results):
        raise typer.Exit(1)
