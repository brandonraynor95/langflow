"""A2A configuration validation for Langflow flows.

Provides validation logic for A2A metadata fields on the Flow model:
slug format, flow eligibility (must contain Agent/LLM components), etc.
"""

from __future__ import annotations

import re

# Component types that indicate conversational / agentic capability.
# A flow must contain at least one of these to be eligible for A2A exposure.
_ELIGIBLE_COMPONENT_TYPES = frozenset({
    # Agent components (primary use case)
    "Agent",
    "AgentComponent",
    # LLM / Chat model components
    "OpenAIModel",
    "ChatOpenAI",
    "AnthropicModel",
    "ChatAnthropic",
    "GoogleGenerativeAIModel",
    "AzureChatOpenAI",
    "OllamaModel",
    "ChatOllama",
    "GroqModel",
    "HuggingFaceModel",
    # Generic markers
    "LLMModel",
    "ChatModel",
    "LanguageModel",
})

# Slug format: lowercase alphanumeric + hyphens, 3-64 chars,
# must start/end with alphanumeric, no consecutive hyphens.
_SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def validate_a2a_slug(slug: str) -> str:
    """Validate that an A2A agent slug is well-formed.

    Rules:
    - 3 to 64 characters
    - Lowercase alphanumeric and hyphens only
    - Must start and end with alphanumeric character
    - No consecutive hyphens

    Returns the validated slug.
    Raises ValueError if invalid.
    """
    if len(slug) < 3:
        msg = "A2A agent slug must be at least 3 characters long."
        raise ValueError(msg)

    if len(slug) > 64:
        msg = "A2A agent slug must be at most 64 characters long."
        raise ValueError(msg)

    if slug != slug.lower():
        msg = "A2A agent slug must be lowercase."
        raise ValueError(msg)

    if not _SLUG_PATTERN.match(slug):
        if slug.startswith("-"):
            msg = "A2A agent slug must start with an alphanumeric character."
            raise ValueError(msg)
        if slug.endswith("-"):
            msg = "A2A agent slug must end with an alphanumeric character."
            raise ValueError(msg)
        msg = "A2A agent slug must contain only lowercase alphanumeric characters and hyphens."
        raise ValueError(msg)

    if "--" in slug:
        msg = "A2A agent slug must not contain consecutive hyphens."
        raise ValueError(msg)

    return slug


def validate_flow_eligible_for_a2a(flow_data: dict | None) -> bool:
    """Check whether a flow's graph data is eligible for A2A exposure.

    A flow is eligible if it contains at least one component whose type
    indicates conversational or agentic capability (Agent, LLM, ChatModel).

    Args:
        flow_data: The flow's saved graph JSON (the `data` field).

    Returns:
        True if eligible, False otherwise.
    """
    if not flow_data:
        return False

    nodes = flow_data.get("nodes", [])
    if not nodes:
        return False

    for node in nodes:
        node_data = node.get("data", {})
        node_type = node_data.get("type", "")
        if node_type in _ELIGIBLE_COMPONENT_TYPES:
            return True

    return False
