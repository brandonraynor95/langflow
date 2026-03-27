"""AgentCard generation from Langflow flow metadata.

Generates A2A-compliant AgentCard dicts from Langflow Flow model instances.
Uses the naming conventions from the a2a-sdk types but outputs plain dicts
for JSON serialization, avoiding a hard dependency on a2a-sdk at import time.

The a2a-sdk types are used for validation in tests, not at generation time.
This keeps the module lightweight and avoids import issues if a2a-sdk is
not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langflow.services.database.models.flow.model import Flow

# Protocol version we target
A2A_PROTOCOL_VERSION = "0.3"

# Default description when neither flow.description nor a2a_description is set
_DEFAULT_DESCRIPTION = "A Langflow agent exposed via the A2A protocol."


def generate_agent_card(flow: Flow, base_url: str) -> dict:
    """Generate an A2A AgentCard from a Langflow flow.

    The card follows the A2A v0.3 spec structure. Field names use
    camelCase to match the protocol JSON schema.

    Args:
        flow: The Langflow Flow model instance. Must have a2a_* fields.
        base_url: The base URL where this agent is hosted
                  (e.g. "https://langflow.example.com/a2a/my-agent").
                  This becomes the `url` field in the card.

    Returns:
        A dict representation of the AgentCard, serializable to JSON.
    """
    # Resolve name: a2a_name takes precedence, fall back to flow.name
    agent_name = getattr(flow, "a2a_name", None) or flow.name

    # Resolve description: a2a_description > flow.description > default
    agent_description = (
        getattr(flow, "a2a_description", None)
        or flow.description
        or _DEFAULT_DESCRIPTION
    )

    # Resolve tags
    tags = getattr(flow, "tags", None) or []

    # Build the single skill representing this flow
    skill = {
        "id": f"flow-{getattr(flow, 'a2a_agent_slug', 'default')}",
        "name": agent_name,
        "description": agent_description,
        "tags": tags,
    }

    # Build the card
    return {
        "name": agent_name,
        "description": agent_description,
        "url": base_url,
        "version": "1.0.0",
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "skills": [skill],
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "supportsAuthenticatedExtendedCard": True,
    }
