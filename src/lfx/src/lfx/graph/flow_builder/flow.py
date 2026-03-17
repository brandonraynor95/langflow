"""Flow creation and inspection.

Pure functions for creating flow dicts and extracting summaries.
"""

from __future__ import annotations


def empty_flow(name: str = "Untitled Flow", description: str = "") -> dict:
    """Create a minimal valid Langflow flow structure."""
    return {
        "name": name,
        "description": description,
        "data": {
            "nodes": [],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        },
    }


def flow_info(flow: dict) -> dict:
    """Extract summary information from a flow dict."""
    data = flow.get("data", {})
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    inputs = []
    outputs = []
    components = []
    for node in nodes:
        node_data = node.get("data", {})
        node_config = node_data.get("node", {})
        display_name = node_config.get("display_name", node_data.get("type", "Unknown"))
        node_type = node_data.get("type", "")
        component_id = node_data.get("id", node.get("id", ""))

        components.append(
            {
                "id": component_id,
                "display_name": display_name,
                "type": node_type,
            }
        )

        if "ChatInput" in node_type or "TextInput" in node_type:
            inputs.append(component_id)
        if "ChatOutput" in node_type or "TextOutput" in node_type:
            outputs.append(component_id)

    return {
        "name": flow.get("name", "Unknown"),
        "description": flow.get("description", ""),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "components": components,
        "inputs": inputs,
        "outputs": outputs,
    }


def flow_graph_repr(flow: dict) -> str:
    """Build an ASCII DAG representation of a flow's graph.

    Uses grandalf for Sugiyama layout when available, falls back to
    a simple chain representation otherwise.
    """
    data = flow.get("data", {})
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not nodes:
        return "(empty)"

    # Build id -> label map
    id_to_label: dict[str, str] = {}
    for node in nodes:
        nd = node.get("data", {})
        nid = nd.get("id", node.get("id", ""))
        id_to_label[nid] = nd.get("type", "?")

    if not edges:
        return ", ".join(sorted(id_to_label.values()))

    vertexes = list(id_to_label.values())
    edge_pairs = []
    for edge in edges:
        src_label = id_to_label.get(edge.get("source", ""))
        tgt_label = id_to_label.get(edge.get("target", ""))
        if src_label and tgt_label:
            edge_pairs.append((src_label, tgt_label))

    try:
        from lfx.graph.graph.ascii import draw_graph

        return draw_graph(vertexes, edge_pairs, return_ascii=True) or "(empty)"
    except Exception:  # noqa: BLE001
        # Fallback: simple chain representation
        return ", ".join(f"{s} -> {t}" for s, t in edge_pairs)
