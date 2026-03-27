"""Integration tests for A2A discovery and configuration endpoints.

These tests verify the full HTTP round-trip for:
1. AgentCard discovery — external agents finding Langflow agents
2. A2A config management — users enabling/disabling A2A on flows

Uses the real FastAPI app, real database (SQLite), and real auth.
Mocks are only used for the instance-level toggle (env var).

Test organization:
- TestAgentCardDiscovery: public AgentCard endpoint behavior
- TestA2AConfigManagement: internal config CRUD endpoints
- TestInstanceToggle: LANGFLOW_A2A_ENABLED kill switch
"""

import pytest
from httpx import AsyncClient

from langflow.services.database.models.flow.model import FlowCreate

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_flow_data() -> dict:
    """Create minimal flow graph data that passes A2A eligibility checks.

    Contains an Agent component node, which makes the flow eligible
    for A2A exposure.
    """
    return {
        "nodes": [
            {
                "id": "chatinput-1",
                "data": {"type": "ChatInput", "node": {"template": {}}},
            },
            {
                "id": "agent-1",
                "data": {"type": "Agent", "node": {"template": {}}},
            },
            {
                "id": "chatoutput-1",
                "data": {"type": "ChatOutput", "node": {"template": {}}},
            },
        ],
        "edges": [
            {"source": "chatinput-1", "target": "agent-1"},
            {"source": "agent-1", "target": "chatoutput-1"},
        ],
    }


def _make_non_agent_flow_data() -> dict:
    """Create flow graph data that does NOT pass A2A eligibility.

    Contains only data-processing nodes — no Agent or LLM.
    """
    return {
        "nodes": [
            {
                "id": "splitter-1",
                "data": {"type": "TextSplitter", "node": {"template": {}}},
            },
        ],
        "edges": [],
    }


async def _create_flow_via_api(
    client: AsyncClient,
    headers: dict,
    *,
    name: str = "Test Agent Flow",
    description: str = "A test flow with an agent",
    data: dict | None = None,
) -> dict:
    """Create a flow via the Langflow API and return the response JSON."""
    if data is None:
        data = _make_agent_flow_data()
    flow = FlowCreate(name=name, description=description, data=data)
    response = await client.post("api/v1/flows/", json=flow.model_dump(), headers=headers)
    assert response.status_code == 201, f"Flow creation failed: {response.text}"
    return response.json()


async def _enable_a2a_on_flow(
    client: AsyncClient,
    headers: dict,
    flow_id: str,
    *,
    slug: str = "test-agent",
):
    """Enable A2A on a flow via the config endpoint."""
    config = {
        "a2a_enabled": True,
        "a2a_agent_slug": slug,
    }
    response = await client.put(
        f"api/v1/flows/{flow_id}/a2a-config",
        json=config,
        headers=headers,
    )
    return response


# ---------------------------------------------------------------------------
# Tests: AgentCard discovery
# ---------------------------------------------------------------------------


class TestAgentCardDiscovery:
    """Tests for the public AgentCard endpoint.

    The AgentCard is how external A2A clients discover what a Langflow
    agent can do. It's served at the well-known URL per the A2A spec.

    The public card requires NO authentication — it's a discovery
    mechanism. The extended card (full skill details) requires auth.
    """

    async def test_enabled_flow_serves_agent_card(self, client: AsyncClient, logged_in_headers):
        """When a flow has A2A enabled, its AgentCard is publicly accessible.

        This is the happy path: create a flow, enable A2A, and verify
        the well-known URL returns a valid AgentCard.
        """
        flow = await _create_flow_via_api(client, logged_in_headers)
        await _enable_a2a_on_flow(client, logged_in_headers, flow["id"], slug="my-agent")

        # The public AgentCard does NOT require auth
        response = await client.get("/a2a/my-agent/.well-known/agent-card.json")

        assert response.status_code == 200
        card = response.json()
        assert card["name"] == "Test Agent Flow"
        assert "skills" in card
        assert "capabilities" in card

    async def test_disabled_flow_returns_404(self, client: AsyncClient, logged_in_headers):
        """When a flow has A2A disabled (the default), the AgentCard
        endpoint returns 404.

        This prevents accidentally exposing internal flows.
        """
        flow = await _create_flow_via_api(client, logged_in_headers)
        # A2A is NOT enabled — default is disabled

        response = await client.get("/a2a/test-agent/.well-known/agent-card.json")
        assert response.status_code == 404

    async def test_nonexistent_slug_returns_404(self, client: AsyncClient):
        """Requesting an AgentCard for a slug that doesn't exist returns 404."""
        response = await client.get("/a2a/nonexistent-agent/.well-known/agent-card.json")
        assert response.status_code == 404

    async def test_extended_card_requires_auth(self, client: AsyncClient, logged_in_headers):
        """The extended card (full skill schemas) requires authentication.

        This protects detailed implementation information from
        unauthenticated discovery.
        """
        flow = await _create_flow_via_api(client, logged_in_headers)
        await _enable_a2a_on_flow(client, logged_in_headers, flow["id"], slug="auth-test-agent")

        # Without auth → 401 or 403
        # Note: httpx maintains cookies across requests, so we must
        # explicitly pass empty/bad auth to override any session state.
        response = await client.get(
            "/a2a/auth-test-agent/v1/card",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code in (401, 403)

        # With valid auth → 200
        response = await client.get("/a2a/auth-test-agent/v1/card", headers=logged_in_headers)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests: A2A config management
# ---------------------------------------------------------------------------


class TestA2AConfigManagement:
    """Tests for the internal A2A config CRUD endpoints.

    These endpoints let Langflow users enable/disable A2A on their flows
    and configure the agent slug, name, and description.
    """

    async def test_enable_a2a_on_flow(self, client: AsyncClient, logged_in_headers):
        """A user can enable A2A on a flow by setting a2a_enabled=True.

        This is the core configuration action — turning a flow into
        a discoverable A2A agent.
        """
        flow = await _create_flow_via_api(client, logged_in_headers)

        response = await _enable_a2a_on_flow(
            client, logged_in_headers, flow["id"], slug="config-test"
        )
        assert response.status_code == 200

        # Verify the config was persisted
        get_response = await client.get(
            f"api/v1/flows/{flow['id']}/a2a-config",
            headers=logged_in_headers,
        )
        assert get_response.status_code == 200
        config = get_response.json()
        assert config["a2a_enabled"] is True
        assert config["a2a_agent_slug"] == "config-test"

    async def test_disable_a2a_on_flow(self, client: AsyncClient, logged_in_headers):
        """A user can disable A2A on a flow, making it undiscoverable."""
        flow = await _create_flow_via_api(client, logged_in_headers)
        await _enable_a2a_on_flow(client, logged_in_headers, flow["id"], slug="disable-test")

        # Disable
        response = await client.put(
            f"api/v1/flows/{flow['id']}/a2a-config",
            json={"a2a_enabled": False},
            headers=logged_in_headers,
        )
        assert response.status_code == 200

        # AgentCard should no longer be accessible
        response = await client.get("/a2a/disable-test/.well-known/agent-card.json")
        assert response.status_code == 404

    async def test_config_requires_auth(self, client: AsyncClient, logged_in_headers):
        """Config endpoints require authentication.

        Unauthenticated users must not be able to enable/disable A2A
        on flows.
        """
        flow = await _create_flow_via_api(client, logged_in_headers)

        # PUT with invalid auth → 401 or 403
        # Note: httpx maintains cookies, so we must explicitly send bad auth
        bad_headers = {"Authorization": "Bearer invalid-token"}
        response = await client.put(
            f"api/v1/flows/{flow['id']}/a2a-config",
            json={"a2a_enabled": True, "a2a_agent_slug": "noauth-test"},
            headers=bad_headers,
        )
        assert response.status_code in (401, 403)

        # GET with invalid auth → 401 or 403
        response = await client.get(
            f"api/v1/flows/{flow['id']}/a2a-config",
            headers=bad_headers,
        )
        assert response.status_code in (401, 403)

    async def test_slug_uniqueness_enforced(self, client: AsyncClient, logged_in_headers):
        """Two flows cannot have the same agent slug.

        The slug is used in the public URL, so collisions would cause
        routing ambiguity.
        """
        flow1 = await _create_flow_via_api(
            client, logged_in_headers, name="Flow One"
        )
        flow2 = await _create_flow_via_api(
            client, logged_in_headers, name="Flow Two"
        )

        # Enable first flow with slug
        response1 = await _enable_a2a_on_flow(
            client, logged_in_headers, flow1["id"], slug="unique-slug"
        )
        assert response1.status_code == 200

        # Try same slug on second flow → should fail
        response2 = await _enable_a2a_on_flow(
            client, logged_in_headers, flow2["id"], slug="unique-slug"
        )
        assert response2.status_code == 409  # Conflict

    async def test_invalid_slug_rejected(self, client: AsyncClient, logged_in_headers):
        """Slug validation is enforced at the API level."""
        flow = await _create_flow_via_api(client, logged_in_headers)

        response = await client.put(
            f"api/v1/flows/{flow['id']}/a2a-config",
            json={"a2a_enabled": True, "a2a_agent_slug": "INVALID SLUG!"},
            headers=logged_in_headers,
        )
        assert response.status_code == 422  # Validation error

    async def test_ineligible_flow_rejected(self, client: AsyncClient, logged_in_headers):
        """A flow without Agent/LLM components cannot be A2A-enabled.

        This prevents exposing data-processing-only flows as A2A agents,
        which would be misleading to external callers.
        """
        flow = await _create_flow_via_api(
            client,
            logged_in_headers,
            name="Data Pipeline",
            data=_make_non_agent_flow_data(),
        )

        response = await _enable_a2a_on_flow(
            client, logged_in_headers, flow["id"], slug="pipeline"
        )
        assert response.status_code == 422  # Not eligible


# ---------------------------------------------------------------------------
# Tests: Instance-level toggle
# ---------------------------------------------------------------------------


class TestInstanceToggle:
    """Tests for the LANGFLOW_A2A_ENABLED instance-level kill switch.

    When this env var is false, ALL A2A routes return 404 — the entire
    subsystem is invisible. This is the rollback mechanism.
    """

    async def test_a2a_disabled_returns_404(self, client: AsyncClient, logged_in_headers, monkeypatch):
        """When LANGFLOW_A2A_ENABLED=false, the AgentCard endpoint
        returns 404 even for an enabled flow.

        This is the master kill switch — it overrides per-flow config.
        """
        monkeypatch.setenv("LANGFLOW_A2A_ENABLED", "false")

        flow = await _create_flow_via_api(client, logged_in_headers)
        await _enable_a2a_on_flow(client, logged_in_headers, flow["id"], slug="killed-agent")

        response = await client.get("/a2a/killed-agent/.well-known/agent-card.json")
        assert response.status_code == 404
