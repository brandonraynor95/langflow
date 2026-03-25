"""Backend wrapper around the shared custom-component flow validation helpers."""

from __future__ import annotations

from lfx.utils.flow_validation import (
    check_flow_and_raise,
)


def validate_flow_custom_components(flow_data: dict | None) -> None:
    """Validate flow data against custom component settings.

    Convenience wrapper that reads the current settings and component cache,
    then delegates to ``check_flow_and_raise``.

    Raises:
        ValueError: If the flow contains blocked or outdated custom components.
    """
    from lfx.interface.components import component_cache

    from langflow.services.deps import get_settings_service

    settings_service = get_settings_service()
    check_flow_and_raise(
        flow_data,
        allow_custom_components=settings_service.settings.allow_custom_components,
        type_to_current_hash=component_cache.type_to_current_hash,
    )
