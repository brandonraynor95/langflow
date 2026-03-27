"""Unit tests for A2A AgentCard generation.

Tests that generate_agent_card() produces a valid, spec-compliant
AgentCard from Langflow flow metadata. These are pure logic tests —
no database, no HTTP.

The AgentCard is the A2A discovery document that tells external agents
what this agent can do, how to authenticate, and what protocol bindings
are supported.
"""

import pytest

from langflow.api.a2a.agent_card import generate_agent_card


# ---------------------------------------------------------------------------
# Fixtures: mock Flow objects
# ---------------------------------------------------------------------------


class MockFlow:
    """Minimal mock of a Flow model for testing AgentCard generation.

    Only includes the fields that agent_card.py needs to read.
    """

    def __init__(
        self,
        *,
        name: str = "My Test Flow",
        description: str | None = "A test flow for unit testing",
        a2a_name: str | None = None,
        a2a_description: str | None = None,
        a2a_agent_slug: str = "my-test-flow",
        tags: list[str] | None = None,
        data: dict | None = None,
    ):
        self.name = name
        self.description = description
        self.a2a_name = a2a_name
        self.a2a_description = a2a_description
        self.a2a_agent_slug = a2a_agent_slug
        self.tags = tags or []
        self.data = data


@pytest.fixture
def basic_flow():
    """A simple flow with default metadata."""
    return MockFlow()


@pytest.fixture
def flow_with_a2a_overrides():
    """A flow with explicit A2A name and description overrides."""
    return MockFlow(
        name="Internal Flow Name",
        description="Internal description",
        a2a_name="Public Agent Name",
        a2a_description="This is the public-facing description for A2A clients.",
        a2a_agent_slug="public-agent",
        tags=["research", "rag"],
    )


@pytest.fixture
def flow_without_description():
    """A flow with no description at all."""
    return MockFlow(description=None, a2a_description=None)


# ---------------------------------------------------------------------------
# Tests: AgentCard structure
# ---------------------------------------------------------------------------


class TestAgentCardStructure:
    """Tests that the generated AgentCard has the correct top-level fields
    and structure required by the A2A protocol.
    """

    def test_card_has_required_fields(self, basic_flow):
        """The card must contain all fields required by the A2A spec:
        name, description, url, version, skills, capabilities, and
        supported protocol bindings.
        """
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")

        assert card["name"] == "My Test Flow"
        assert card["description"] == "A test flow for unit testing"
        assert card["url"] == "http://localhost:7860/a2a/my-test-flow"
        assert "version" in card
        assert "skills" in card
        assert "capabilities" in card
        assert "defaultInputModes" in card
        assert "defaultOutputModes" in card

    def test_card_uses_a2a_name_when_set(self, flow_with_a2a_overrides):
        """When a2a_name is set on the flow, it takes precedence over flow.name.

        This lets users give their agent a public-facing name that differs
        from the internal flow name.
        """
        card = generate_agent_card(
            flow_with_a2a_overrides,
            base_url="http://localhost:7860/a2a/public-agent",
        )

        assert card["name"] == "Public Agent Name"
        assert card["description"] == "This is the public-facing description for A2A clients."

    def test_card_falls_back_to_flow_name_when_a2a_name_not_set(self, basic_flow):
        """When a2a_name is None, the card uses flow.name instead."""
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert card["name"] == "My Test Flow"

    def test_card_uses_default_description_when_none(self, flow_without_description):
        """When both flow.description and a2a_description are None,
        the card provides a sensible default instead of null.

        A2A clients should always see *something* in the description field.
        """
        card = generate_agent_card(
            flow_without_description,
            base_url="http://localhost:7860/a2a/my-test-flow",
        )
        assert card["description"] is not None
        assert len(card["description"]) > 0


# ---------------------------------------------------------------------------
# Tests: Capabilities
# ---------------------------------------------------------------------------


class TestAgentCardCapabilities:
    """Tests that the capabilities section accurately reflects what
    Langflow's A2A server supports.

    Honest capability advertising is a product principle — the card
    must not claim features that aren't implemented.
    """

    def test_streaming_is_enabled(self, basic_flow):
        """Langflow supports SSE streaming from day one, so
        capabilities.streaming must be True.
        """
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert card["capabilities"]["streaming"] is True

    def test_push_notifications_are_disabled(self, basic_flow):
        """Push notifications are not in v1 scope, so the card must
        honestly advertise pushNotifications=False.
        """
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert card["capabilities"]["pushNotifications"] is False

    def test_state_transition_history_is_disabled(self, basic_flow):
        """State transition history is not in v1 scope."""
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert card["capabilities"]["stateTransitionHistory"] is False


# ---------------------------------------------------------------------------
# Tests: Skills
# ---------------------------------------------------------------------------


class TestAgentCardSkills:
    """Tests that the AgentCard skills section correctly represents
    the flow's capabilities.

    In v1, each flow maps to exactly one skill.
    """

    def test_card_has_exactly_one_skill(self, basic_flow):
        """Each A2A-exposed flow is represented as a single skill.

        A flow does one thing (its graph), so one skill is the right
        abstraction for v1.
        """
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert len(card["skills"]) == 1

    def test_skill_uses_flow_metadata(self, basic_flow):
        """The skill's name and description come from the flow."""
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        skill = card["skills"][0]

        assert skill["name"] == "My Test Flow"
        assert skill["description"] == "A test flow for unit testing"
        assert "id" in skill

    def test_skill_includes_tags(self, flow_with_a2a_overrides):
        """Flow tags are propagated to the skill for discoverability."""
        card = generate_agent_card(
            flow_with_a2a_overrides,
            base_url="http://localhost:7860/a2a/public-agent",
        )
        skill = card["skills"][0]
        assert skill["tags"] == ["research", "rag"]

    def test_skill_has_empty_tags_when_flow_has_none(self, basic_flow):
        """When flow has no tags, skill tags is an empty list (not None)."""
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        skill = card["skills"][0]
        assert skill["tags"] == []


# ---------------------------------------------------------------------------
# Tests: Protocol binding
# ---------------------------------------------------------------------------


class TestAgentCardProtocol:
    """Tests that the AgentCard correctly declares the protocol binding.

    Langflow's v1 A2A server uses the HTTP+JSON/REST binding.
    """

    def test_default_input_modes(self, basic_flow):
        """The agent accepts text input by default."""
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert "text" in card["defaultInputModes"]

    def test_default_output_modes(self, basic_flow):
        """The agent produces text output by default."""
        card = generate_agent_card(basic_flow, base_url="http://localhost:7860/a2a/my-test-flow")
        assert "text" in card["defaultOutputModes"]
