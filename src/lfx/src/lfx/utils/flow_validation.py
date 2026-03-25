"""Shared flow validation helpers for custom component policy enforcement."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from lfx.log.logger import logger
from lfx.utils.component_aliases import get_component_type_aliases

INITIALIZING_COMPONENT_TEMPLATES_MESSAGE = (
    "Flow build blocked: component templates are still initializing. Please try again in a few seconds."
)


def _compute_code_hash(code: str) -> str:
    """Compute the 12-char SHA256 prefix used by the component index."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]


def collect_component_hash_lookups(
    all_types_dict: Mapping[str, Any],
) -> tuple[dict[str, str], set[str]]:
    """Build code-hash lookups for components and their aliases."""
    type_to_hash: dict[str, str] = {}
    all_hashes: set[str] = set()

    for category_components in all_types_dict.values():
        if not isinstance(category_components, Mapping):
            continue

        for component_name, component_data in category_components.items():
            if not isinstance(component_data, Mapping):
                continue

            metadata = component_data.get("metadata")
            if not isinstance(metadata, Mapping):
                continue

            code_hash = metadata.get("code_hash")
            if not isinstance(code_hash, str) or not code_hash:
                continue

            all_hashes.add(code_hash)
            for alias in get_component_type_aliases(component_name, component_data):
                type_to_hash.setdefault(alias, code_hash)

    return type_to_hash, all_hashes


def _get_invalid_components(
    nodes: list[dict],
    type_to_current_hash: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Walk nodes and classify invalid components."""
    blocked: list[str] = []
    outdated: list[str] = []

    for node in nodes:
        node_data = node.get("data", {})
        node_info = node_data.get("node", {})

        component_type = node_data.get("type")
        if not component_type:
            continue

        node_template = node_info.get("template", {})
        node_code_field = node_template.get("code", {})
        node_code = node_code_field.get("value") if isinstance(node_code_field, dict) else None

        if not node_code:
            continue

        display_name = node_info.get("display_name") or component_type
        node_id = node_data.get("id") or node.get("id", "unknown")
        label = f"{display_name} ({node_id})"

        expected_hash = type_to_current_hash.get(component_type)
        if expected_hash is None:
            blocked.append(label)
        else:
            node_hash = _compute_code_hash(node_code)
            if node_hash != expected_hash:
                outdated.append(label)

        flow_data = node_info.get("flow", {})
        if isinstance(flow_data, dict):
            nested_data = flow_data.get("data", {})
            nested_nodes = nested_data.get("nodes", [])
            if nested_nodes:
                nested_blocked, nested_outdated = _get_invalid_components(
                    nested_nodes,
                    type_to_current_hash,
                )
                blocked.extend(nested_blocked)
                outdated.extend(nested_outdated)

    return blocked, outdated


def code_hash_matches_any_template(code: str, all_known_hashes: set[str]) -> bool:
    """Check whether code matches any known component template hash."""
    return _compute_code_hash(code) in all_known_hashes


def check_flow_and_raise(
    flow_data: dict | None,
    *,
    allow_custom_components: bool,
    type_to_current_hash: dict[str, str] | None = None,
) -> None:
    """Validate flow component code against known server templates."""
    if allow_custom_components or not flow_data:
        return

    nodes = flow_data.get("nodes", [])
    if not nodes:
        return

    if type_to_current_hash is None:
        logger.error(
            "Flow validation requested but component hash lookups are not yet loaded. "
            "Blocking execution as a safety measure."
        )
        raise ValueError(INITIALIZING_COMPONENT_TEMPLATES_MESSAGE)

    blocked, outdated = _get_invalid_components(nodes, type_to_current_hash)

    if blocked:
        blocked_names = ", ".join(blocked)
        logger.warning(f"Flow build blocked: unrecognized component code: {blocked_names}")
        message = f"Flow build blocked: custom components are not allowed: {blocked_names}"
        raise ValueError(message)

    if outdated:
        outdated_names = ", ".join(outdated)
        logger.warning(f"Flow build blocked: outdated components must be updated: {outdated_names}")
        message = f"Flow build blocked: outdated components must be updated before running: {outdated_names}"
        raise ValueError(message)


async def ensure_component_hash_lookups_loaded() -> dict[str, str] | None:
    """Ensure component hash lookups are available for CLI/runtime validation."""
    from lfx.interface.components import component_cache, get_and_cache_all_types_dict
    from lfx.services.deps import get_settings_service

    settings_service = get_settings_service()
    if settings_service is None:
        return None

    if not settings_service.settings.allow_custom_components and component_cache.type_to_current_hash is None:
        try:
            await get_and_cache_all_types_dict(settings_service)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to populate component template hash lookups", exc_info=exc)

    return component_cache.type_to_current_hash


async def validate_lfx_flow_custom_components(flow_data: dict | None) -> None:
    """Validate raw flow data using the active LFX settings."""
    from lfx.services.deps import get_settings_service

    settings_service = get_settings_service()
    if settings_service is None:
        msg = "Settings service must be initialized before validating LFX flows."
        raise RuntimeError(msg)

    allow_custom_components = settings_service.settings.allow_custom_components
    type_to_current_hash = await ensure_component_hash_lookups_loaded() if not allow_custom_components else None

    check_flow_and_raise(
        flow_data,
        allow_custom_components=allow_custom_components,
        type_to_current_hash=type_to_current_hash,
    )


async def validate_lfx_graph_custom_components(graph: Any) -> None:
    """Validate a prepared graph before execution."""
    await validate_lfx_flow_custom_components(getattr(graph, "raw_graph_data", None))
