"""Unit tests for LFX flow validation helpers."""

import pytest
from lfx.utils.flow_validation import validate_lfx_flow_custom_components


def _blocked_raw_graph() -> dict:
    return {
        "nodes": [
            {
                "id": "node-1",
                "data": {
                    "id": "node-1",
                    "type": "TotallyCustom",
                    "node": {
                        "display_name": "Blocked Node",
                        "template": {
                            "code": {"value": "print('blocked')"},
                        },
                    },
                },
            }
        ],
        "edges": [],
    }


@pytest.mark.asyncio
async def test_validate_lfx_flow_custom_components_requires_settings_service(mocker):
    """Validation should fail loudly when the settings service is unavailable."""
    mocker.patch("lfx.services.deps.get_settings_service", return_value=None)

    with pytest.raises(RuntimeError, match="Settings service must be initialized"):
        await validate_lfx_flow_custom_components(_blocked_raw_graph())
