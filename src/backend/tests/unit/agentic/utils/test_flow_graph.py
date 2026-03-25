from types import SimpleNamespace

import pytest
from langflow.agentic.utils.flow_graph import get_flow_graph_summary
from lfx.interface.components import component_cache


@pytest.mark.asyncio
async def test_get_flow_graph_summary_blocks_custom_components(monkeypatch):
    blocked_flow = SimpleNamespace(
        id="flow-1",
        name="Blocked Flow",
        tags=[],
        description="Contains blocked custom code",
        data={
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
        },
    )

    async def _get_flow(*_args, **_kwargs):
        return blocked_flow

    monkeypatch.setattr("langflow.agentic.utils.flow_graph.get_flow_by_id_or_endpoint_name", _get_flow)
    monkeypatch.setattr(
        "lfx.services.deps.get_settings_service",
        lambda: SimpleNamespace(settings=SimpleNamespace(allow_custom_components=False)),
    )
    monkeypatch.setattr(component_cache, "type_to_current_hash", {"ChatInput": "known-hash"})
    monkeypatch.setattr(component_cache, "all_types_dict", None)

    result = await get_flow_graph_summary("flow-1")

    assert "custom components are not allowed" in result["error"]
