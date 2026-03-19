"""lfx validate -- structural and semantic validation of Langflow flow JSON.

Validation levels (each level implies all levels below it):

    Level 1 - structural
        The file parses as valid JSON and contains the expected top-level keys
        (``id``, ``name``, ``data``, ``data.nodes``, ``data.edges``).
        Also checks for orphaned nodes (no edges at all) and unused nodes
        (not reachable from any output node), and warns about version mismatches
        (nodes built with a different Langflow version than the one installed).

    Level 2 - components
        Every node's ``data.type`` references a component type that exists in
        the lfx component registry.

    Level 3 - edge types
        Connected ports carry compatible types (source output type must be
        assignable to target input type).

    Level 4 - required inputs
        Every required input field on every component has a value or an
        incoming edge connected to it.  Also checks that password/secret fields
        have a value or a matching environment variable set.

Use ``--level`` to select how deep to go, or ``--skip-*`` flags to opt out of
individual checks while still running the others.

Pass ``--strict`` to treat warnings as errors (exit code 1).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

console = Console(stderr=True)
ok_console = Console()

# Validation level constants
_LEVEL_STRUCTURAL = 1
_LEVEL_COMPONENTS = 2
_LEVEL_EDGE_TYPES = 3
_LEVEL_REQUIRED_INPUTS = 4


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
# Level 1 - structural checks (pure JSON, no component loading)
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
                level=_LEVEL_STRUCTURAL,
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
                level=_LEVEL_STRUCTURAL,
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
                level=_LEVEL_STRUCTURAL,
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
                level=_LEVEL_STRUCTURAL,
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
                    level=_LEVEL_STRUCTURAL,
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
                        level=_LEVEL_STRUCTURAL,
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
                    level=_LEVEL_STRUCTURAL,
                    severity="warning",
                    node_id=node.get("id"),
                    node_name=_node_display_name(node),
                    message="Node is missing 'data.type' -- component type cannot be determined",
                )
            )

    return ok


def _node_display_name(node: dict[str, Any]) -> str | None:
    return node.get("data", {}).get("node", {}).get("display_name") or node.get("data", {}).get("id") or node.get("id")


# ---------------------------------------------------------------------------
# Level 1 (continued) - orphaned and unused node checks
# ---------------------------------------------------------------------------


def _check_orphaned_nodes(flow: dict[str, Any], result: ValidationResult) -> None:
    """Warn about nodes that have no edges connecting them to the rest of the graph.

    A node is *orphaned* when it appears in no edge (neither as source nor as
    target).  Single-node flows are exempt.
    """
    data = flow.get("data", {})
    nodes: list[dict[str, Any]] = [n for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n]
    edges: list[dict[str, Any]] = [e for e in data.get("edges", []) if isinstance(e, dict)]

    if len(nodes) <= 1:
        return  # single-node flows are always "connected"

    connected_ids: set[str] = set()
    for edge in edges:
        if edge.get("source"):
            connected_ids.add(edge["source"])
        if edge.get("target"):
            connected_ids.add(edge["target"])

    for node in nodes:
        node_id = node["id"]
        if node_id not in connected_ids:
            result.issues.append(
                ValidationIssue(
                    level=_LEVEL_STRUCTURAL,
                    severity="warning",
                    node_id=node_id,
                    node_name=_node_display_name(node),
                    message="Orphaned node: not connected to any other node",
                )
            )


def _check_unused_nodes(flow: dict[str, Any], result: ValidationResult) -> None:
    """Warn about nodes whose outputs never reach an output node.

    Walks the graph backwards from every node whose ``data.type`` ends with
    ``"Output"`` (e.g. ``ChatOutput``, ``TextOutput``).  Any node that is not
    reachable from an output node is considered unused.

    Single-node flows and flows with no output nodes are skipped.
    """
    data = flow.get("data", {})
    nodes: list[dict[str, Any]] = [n for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n]
    edges: list[dict[str, Any]] = [e for e in data.get("edges", []) if isinstance(e, dict)]

    if len(nodes) <= 1:
        return

    # Build reverse adjacency: for each node, which nodes feed INTO it
    # (i.e. target -> {sources})
    predecessors: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src and tgt and tgt in predecessors:
            predecessors[tgt].add(src)

    # Identify output nodes by type suffix
    output_node_ids: set[str] = set()
    for node in nodes:
        component_type: str = node.get("data", {}).get("type", "") or ""
        if component_type.endswith("Output"):
            output_node_ids.add(node["id"])

    if not output_node_ids:
        return  # can't determine "useful" without knowing output nodes

    # BFS backwards from all output nodes to find every contributing node
    reachable: set[str] = set()
    queue: list[str] = list(output_node_ids)
    while queue:
        current = queue.pop()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(predecessors.get(current, set()) - reachable)

    nodes_by_id = {n["id"]: n for n in nodes}
    for node_id, node in nodes_by_id.items():
        if node_id not in reachable:
            result.issues.append(
                ValidationIssue(
                    level=_LEVEL_STRUCTURAL,
                    severity="warning",
                    node_id=node_id,
                    node_name=_node_display_name(node),
                    message="Unused node: does not contribute to any output",
                )
            )


# ---------------------------------------------------------------------------
# Level 2 - component existence (loads lfx component registry)
# ---------------------------------------------------------------------------


def _check_component_existence(flow: dict[str, Any], result: ValidationResult) -> None:
    try:
        from lfx.interface.utils import initialize_components  # type: ignore[import-untyped]

        component_registry: set[str] = set(initialize_components().keys())
    except Exception as exc:  # noqa: BLE001
        result.issues.append(
            ValidationIssue(
                level=_LEVEL_COMPONENTS,
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
                    level=_LEVEL_COMPONENTS,
                    severity="error",
                    node_id=node.get("id"),
                    node_name=_node_display_name(node),
                    message=(f"Unknown component type '{component_type}'. This component may be missing or outdated."),
                )
            )


# ---------------------------------------------------------------------------
# Level 3 - edge type compatibility
# ---------------------------------------------------------------------------


def _check_edge_type_compatibility(flow: dict[str, Any], result: ValidationResult) -> None:
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
                    level=_LEVEL_EDGE_TYPES,
                    severity="error",
                    node_id=None,
                    node_name=None,
                    message=(f"Edge references non-existent node(s): source={src_id!r}, target={tgt_id!r}"),
                )
            )
            continue

        output_types: list[str] = src_handle.get("output_types", [])
        src_type: str | None = output_types[0] if output_types else None
        tgt_type: str | None = tgt_handle.get("type")

        if src_type and tgt_type and tgt_type not in {src_type, "Any"}:
            result.issues.append(
                ValidationIssue(
                    level=_LEVEL_EDGE_TYPES,
                    severity="warning",
                    node_id=tgt_id,
                    node_name=_node_display_name(tgt_node),
                    message=(
                        f"Possible type mismatch on edge from "
                        f"'{_node_display_name(src_node)}' -> '{_node_display_name(tgt_node)}': "
                        f"source emits '{src_type}', target expects '{tgt_type}'"
                    ),
                )
            )


# ---------------------------------------------------------------------------
# Extended check helpers
# ---------------------------------------------------------------------------


def _get_lf_version() -> str | None:
    """Return the installed Langflow version string, or *None* if not installed.

    Tries the four known package names in order of preference so the check
    works with released builds, nightly builds, and editable installs.
    """
    from importlib.metadata import PackageNotFoundError, version

    for pkg in ("langflow-base", "langflow", "langflow-base-nightly", "langflow-nightly"):
        try:
            return version(pkg)
        except PackageNotFoundError:
            continue
    return None


# ---------------------------------------------------------------------------
# Extended check 1 - version mismatch / outdated components
# ---------------------------------------------------------------------------


def _check_version_mismatch(flow: dict[str, Any], result: ValidationResult) -> None:
    """Warn when nodes were built with a different Langflow version.

    Each unique ``lf_version`` embedded in the node metadata that differs from
    the currently installed Langflow version triggers a single warning covering
    all affected nodes.  If Langflow is not installed the check is skipped
    silently (lfx can run standalone).

    This covers both "outdated components" (node built with an older release)
    and "version mismatch" (node built with any different release).
    """
    installed = _get_lf_version()
    if installed is None:
        return  # Langflow not installed; skip silently

    nodes: list[dict[str, Any]] = [n for n in flow.get("data", {}).get("nodes", []) if isinstance(n, dict)]

    # Collect node IDs grouped by the version they were built with
    version_to_nodes: dict[str, list[str]] = {}
    for node in nodes:
        lf_version: str | None = node.get("data", {}).get("node", {}).get("lf_version")
        if lf_version and lf_version != installed:
            version_to_nodes.setdefault(lf_version, []).append(_node_display_name(node) or node.get("id") or "?")

    _max_sample = 3
    for built_version, node_names in sorted(version_to_nodes.items()):
        count = len(node_names)
        sample = ", ".join(node_names[:_max_sample]) + (" …" if count > _max_sample else "")
        result.issues.append(
            ValidationIssue(
                level=_LEVEL_STRUCTURAL,
                severity="warning",
                node_id=None,
                node_name=None,
                message=(
                    f"{count} component(s) built with Langflow {built_version} "
                    f"(installed: {installed}) — re-export recommended. "
                    f"Affected: {sample}"
                ),
            )
        )


# ---------------------------------------------------------------------------
# Extended check 2 - missing credentials
# ---------------------------------------------------------------------------


def _check_missing_credentials(flow: dict[str, Any], result: ValidationResult) -> None:
    """Warn when password/secret fields have no value and no matching env var.

    A template field is considered a *credential field* when it has
    ``"password": true`` (or ``"display_password": true``).  If no value is
    stored in the flow JSON *and* no corresponding environment variable is set
    *and* the field has no incoming edge, a warning is emitted so the user
    knows to provide the secret before running the flow.

    The environment variable name is derived by uppercasing the field name and
    replacing hyphens with underscores (e.g. ``openai_api_key`` →
    ``OPENAI_API_KEY``).
    """
    data = flow.get("data", {})
    edges = data.get("edges", [])

    # Build the set of (node_id, field_name) pairs that receive an edge
    connected_inputs: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        tgt_id = edge.get("target")
        tgt_handle = edge.get("data", {}).get("targetHandle", {}) or {}
        field_name = tgt_handle.get("fieldName")
        if tgt_id and field_name:
            connected_inputs.add((tgt_id, field_name))

    for node in data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_data = node.get("data", {})
        template: dict[str, Any] = node_data.get("node", {}).get("template", {})

        for field_name, field_def in template.items():
            if field_name.startswith("_") or not isinstance(field_def, dict):
                continue

            is_credential = field_def.get("password", False) or field_def.get("display_password", False)
            if not is_credential:
                continue

            show = field_def.get("show", True)
            if not show:
                continue

            # Already satisfied? Check value, incoming edge, or env var.
            has_value = bool(field_def.get("value"))
            has_edge = (node_id, field_name) in connected_inputs
            if has_value or has_edge:
                continue

            env_key = field_name.upper().replace("-", "_")
            if os.environ.get(env_key):
                continue

            result.issues.append(
                ValidationIssue(
                    level=_LEVEL_REQUIRED_INPUTS,
                    severity="warning",
                    node_id=node_id,
                    node_name=_node_display_name(node),
                    message=(
                        f"Credential field '{field_name}' has no value "
                        f"(set ${env_key} or configure via global variables)"
                    ),
                )
            )


# ---------------------------------------------------------------------------
# Level 4 - required inputs connected
# ---------------------------------------------------------------------------


def _check_required_inputs(flow: dict[str, Any], result: ValidationResult) -> None:
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
                        level=_LEVEL_REQUIRED_INPUTS,
                        severity="error",
                        node_id=node_id,
                        node_name=_node_display_name(node),
                        message=f"Required input '{field_name}' has no value and no incoming edge",
                    )
                )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_flow_file(
    path: Path,
    *,
    level: int = _LEVEL_REQUIRED_INPUTS,
    skip_components: bool = False,
    skip_edge_types: bool = False,
    skip_required_inputs: bool = False,
    skip_version_check: bool = False,
    skip_credentials: bool = False,
) -> ValidationResult:
    result = ValidationResult(path=path)

    try:
        raw = path.read_text(encoding="utf-8")
        flow: dict[str, Any] = json.loads(raw)
    except (OSError, PermissionError) as exc:
        result.issues.append(
            ValidationIssue(
                level=_LEVEL_STRUCTURAL,
                severity="error",
                node_id=None,
                node_name=None,
                message=f"Cannot read file: {exc}",
            )
        )
        return result
    except json.JSONDecodeError as exc:
        result.issues.append(
            ValidationIssue(
                level=_LEVEL_STRUCTURAL,
                severity="error",
                node_id=None,
                node_name=None,
                message=f"Invalid JSON: {exc}",
            )
        )
        return result

    # Level 1 - structural (JSON shape + orphaned/unused node checks)
    can_continue = _check_structural(flow, result)
    if can_continue:
        _check_orphaned_nodes(flow, result)
        _check_unused_nodes(flow, result)
        # Extended: version mismatch / outdated components
        if not skip_version_check:
            _check_version_mismatch(flow, result)
    if not can_continue or level < _LEVEL_COMPONENTS:
        return result

    # Level 2 - component existence
    if not skip_components:
        _check_component_existence(flow, result)
    if level < _LEVEL_EDGE_TYPES:
        return result

    # Level 3 - edge type compatibility
    if not skip_edge_types:
        _check_edge_type_compatibility(flow, result)
    if level < _LEVEL_REQUIRED_INPUTS:
        return result

    # Level 4 - required inputs + extended: missing credentials
    if not skip_required_inputs:
        _check_required_inputs(flow, result)
    if not skip_credentials:
        _check_missing_credentials(flow, result)

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _render_results(results: list[ValidationResult], *, verbose: bool, strict: bool = False) -> None:
    for result in results:
        label = f"[bold]{result.path}[/bold]"
        passes = result.ok and not (strict and result.warnings)
        if passes:
            ok_console.print(f"[green]\u2713[/green] {label}")
        else:
            console.print(f"[red]\u2717[/red] {label}")

        show_issues = verbose or not passes
        if show_issues:
            for issue in result.issues:
                # In strict mode warnings are shown as errors
                effective_severity = "error" if (strict and issue.severity == "warning") else issue.severity
                color = "red" if effective_severity == "error" else "yellow"
                loc = f" [{issue.node_name or issue.node_id}]" if (issue.node_id or issue.node_name) else ""
                console.print(
                    f"  [{color}][L{issue.level} {effective_severity.upper()}][/{color}]{loc} {issue.message}"
                )


def _expand_paths(raw_paths: list[str]) -> list[Path]:
    """Expand each entry to a list of .json files.

    * If the path is a directory, collect every ``*.json`` file recursively.
    * If the path is a file, return it as-is.
    * If the path does not exist, print an error and exit 2.
    """
    paths: list[Path] = []
    for raw in raw_paths:
        p = Path(raw)
        if not p.exists():
            console.print(f"[red]Error:[/red] Path not found: {p}")
            raise typer.Exit(2)
        if p.is_dir():
            found = sorted(p.rglob("*.json"))
            if not found:
                console.print(f"[yellow]Warning:[/yellow] No .json files found in {p}")
            paths.extend(found)
        else:
            paths.append(p)
    return paths


def validate_command(
    flow_paths: list[str],
    level: int,
    *,
    skip_components: bool,
    skip_edge_types: bool,
    skip_required_inputs: bool,
    skip_version_check: bool,
    skip_credentials: bool,
    strict: bool,
    verbose: bool,
    output_format: str,
) -> None:
    paths = _expand_paths(flow_paths)

    if not paths:
        console.print("[yellow]No flow files to validate.[/yellow]")
        raise typer.Exit(0)

    results = [
        validate_flow_file(
            p,
            level=level,
            skip_components=skip_components,
            skip_edge_types=skip_edge_types,
            skip_required_inputs=skip_required_inputs,
            skip_version_check=skip_version_check,
            skip_credentials=skip_credentials,
        )
        for p in paths
    ]

    if output_format == "json":
        import json as _json

        out = [
            {
                "path": str(r.path),
                "ok": r.ok if not strict else (not r.errors and not r.warnings),
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
            }
            for r in results
        ]
        sys.stdout.write(_json.dumps(out, indent=2) + "\n")
    else:
        _render_results(results, verbose=verbose, strict=strict)

    failed = any((not r.ok) or (strict and r.warnings) for r in results)
    if failed:
        raise typer.Exit(1)
