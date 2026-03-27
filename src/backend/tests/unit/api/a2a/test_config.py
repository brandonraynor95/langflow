"""Unit tests for A2A configuration validation.

Tests the validation logic that determines whether a flow can be exposed
as an A2A agent, and whether the agent slug is well-formed.

These are pure logic tests — no database, no HTTP, no auth.
"""

import pytest

from langflow.api.a2a.config import validate_a2a_slug, validate_flow_eligible_for_a2a


# ---------------------------------------------------------------------------
# validate_a2a_slug: format rules
# ---------------------------------------------------------------------------


class TestValidateA2ASlug:
    """Tests for the agent slug format validator.

    The slug appears in the public URL: /a2a/{agent_slug}/v1/message:send
    It must be safe, readable, and stable as a URL path segment.
    """

    def test_valid_simple_slug(self):
        """A short lowercase alphanumeric slug is accepted."""
        assert validate_a2a_slug("my-agent") == "my-agent"

    def test_valid_numeric_slug(self):
        """Slugs can contain numbers."""
        assert validate_a2a_slug("agent-v2") == "agent-v2"

    def test_valid_minimum_length(self):
        """Minimum length is 3 characters."""
        assert validate_a2a_slug("abc") == "abc"

    def test_valid_maximum_length(self):
        """Maximum length is 64 characters."""
        slug = "a" * 64
        assert validate_a2a_slug(slug) == slug

    def test_rejects_too_short(self):
        """Slugs shorter than 3 characters are rejected."""
        with pytest.raises(ValueError, match="at least 3"):
            validate_a2a_slug("ab")

    def test_rejects_empty_string(self):
        """Empty string is rejected."""
        with pytest.raises(ValueError, match="at least 3"):
            validate_a2a_slug("")

    def test_rejects_too_long(self):
        """Slugs longer than 64 characters are rejected."""
        with pytest.raises(ValueError, match="at most 64"):
            validate_a2a_slug("a" * 65)

    def test_rejects_uppercase(self):
        """Uppercase letters are not allowed (URL consistency)."""
        with pytest.raises(ValueError, match="lowercase"):
            validate_a2a_slug("My-Agent")

    def test_rejects_underscores(self):
        """Underscores are not allowed — hyphens only for separators."""
        with pytest.raises(ValueError, match="lowercase alphanumeric"):
            validate_a2a_slug("my_agent")

    def test_rejects_spaces(self):
        """Spaces are not allowed in URL path segments."""
        with pytest.raises(ValueError, match="lowercase alphanumeric"):
            validate_a2a_slug("my agent")

    def test_rejects_special_characters(self):
        """Special characters like dots and slashes are not allowed."""
        with pytest.raises(ValueError, match="lowercase alphanumeric"):
            validate_a2a_slug("my.agent")

    def test_rejects_leading_hyphen(self):
        """Slug must start with an alphanumeric character."""
        with pytest.raises(ValueError, match="start.*alphanumeric"):
            validate_a2a_slug("-my-agent")

    def test_rejects_trailing_hyphen(self):
        """Slug must end with an alphanumeric character."""
        with pytest.raises(ValueError, match="end.*alphanumeric"):
            validate_a2a_slug("my-agent-")

    def test_rejects_consecutive_hyphens(self):
        """No double hyphens — prevents visual confusion and is DNS-label-safe."""
        with pytest.raises(ValueError, match="consecutive"):
            validate_a2a_slug("my--agent")

    def test_all_numeric_allowed(self):
        """A purely numeric slug is allowed (unusual but valid)."""
        assert validate_a2a_slug("123") == "123"


# ---------------------------------------------------------------------------
# validate_flow_eligible_for_a2a: flow graph inspection
# ---------------------------------------------------------------------------


class TestValidateFlowEligibility:
    """Tests for the flow eligibility checker.

    Only flows that can process conversational input are eligible for
    A2A exposure in v1. This means the flow graph must contain at least
    one agent or LLM component — a pure data-processing DAG is not eligible.

    The checker inspects the flow's `data` dict (the saved graph JSON)
    to find component types.
    """

    def test_flow_with_agent_component_is_eligible(self):
        """A flow containing an Agent component is eligible.

        The Agent component is the primary use case — it can reason,
        use tools, and maintain conversation context.
        """
        flow_data = _make_flow_data_with_node_types(["Agent"])
        assert validate_flow_eligible_for_a2a(flow_data) is True

    def test_flow_with_llm_component_is_eligible(self):
        """A flow containing an LLM/ChatModel component is eligible.

        Even without a full Agent, an LLM-backed flow can process
        natural language input and produce text output.
        """
        flow_data = _make_flow_data_with_node_types(["OpenAIModel"])
        assert validate_flow_eligible_for_a2a(flow_data) is True

    def test_flow_with_chat_input_and_agent_is_eligible(self):
        """A typical agent flow with ChatInput + Agent is eligible."""
        flow_data = _make_flow_data_with_node_types(["ChatInput", "Agent", "ChatOutput"])
        assert validate_flow_eligible_for_a2a(flow_data) is True

    def test_pure_data_processing_flow_is_not_eligible(self):
        """A flow with only data-processing components is NOT eligible.

        These flows have no conversational capability — they can't
        process natural language or maintain context. Exposing them
        via A2A would be misleading.
        """
        flow_data = _make_flow_data_with_node_types(["TextSplitter", "Embeddings"])
        assert validate_flow_eligible_for_a2a(flow_data) is False

    def test_empty_flow_data_is_not_eligible(self):
        """A flow with no graph data cannot be exposed."""
        assert validate_flow_eligible_for_a2a(None) is False

    def test_flow_with_empty_nodes_is_not_eligible(self):
        """A flow with an empty nodes list has no components."""
        flow_data = {"nodes": [], "edges": []}
        assert validate_flow_eligible_for_a2a(flow_data) is False

    def test_eligibility_checks_node_type_field(self):
        """The checker inspects the node's type field (component class name)."""
        # Verify it works with the actual node data structure
        flow_data = {
            "nodes": [
                {
                    "id": "node-1",
                    "data": {
                        "type": "Agent",
                        "node": {"template": {}},
                    },
                }
            ],
            "edges": [],
        }
        assert validate_flow_eligible_for_a2a(flow_data) is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flow_data_with_node_types(node_types: list[str]) -> dict:
    """Create minimal flow graph data with the given component types.

    This mimics the structure of Langflow's saved flow JSON,
    specifically the parts the eligibility checker needs to inspect.
    """
    nodes = []
    for i, node_type in enumerate(node_types):
        nodes.append(
            {
                "id": f"node-{i}",
                "data": {
                    "type": node_type,
                    "node": {"template": {}},
                },
            }
        )
    return {"nodes": nodes, "edges": []}
