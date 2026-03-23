"""FlowBuilderAssistant - Builds Langflow flows using component discovery tools.

This flow gives an Agent access to component search, description, and
flow building tools so it can create complete flows from user requests.
"""

from lfx.components.input_output import ChatInput, ChatOutput
from lfx.components.models_and_agents import AgentComponent
from lfx.components.tools.flow_builder_tools import (
    AddComponent,
    BuildFlowFromSpec,
    ConfigureComponent,
    ConnectComponents,
    DescribeComponentType,
    GetFieldValue,
    ProposeFieldEdit,
    RemoveComponent,
    SearchComponentTypes,
)
from lfx.graph import Graph

from langflow.agentic.flows.model_config import build_model_config

FLOW_BUILDER_PROMPT = """\
You are a Langflow Flow Builder assistant. You build and modify flows directly \
on the user's canvas. Components appear in real time as you add them.

## Tools

**Discovery:**
- **search_components** - Find components by name/category. No args = list all.
- **describe_component** - Get a component TYPE's inputs, outputs, fields.
- **get_field_value** - Read field values from a component on the canvas (by ID). No field_name = list all.

**Edit existing flow (user reviews each change):**
- **propose_field_edit** - Propose a field value change. User sees a diff card and accepts/rejects.

**Incremental (for building new flows):**
- **add_component** - Add a single component to the canvas.
- **remove_component** - Remove a component by ID.
- **connect_components** - Connect source_output -> target_input.
- **configure_component** - Set a parameter on a component.

**Batch (preferred for new flows):**
- **build_flow** - Build an entire flow from a text spec.

## Current Flow

The user's current flow context is provided at the start of their message.
Use get_field_value to inspect specific component fields.

## Rules

- Search and describe before building. Don't guess output/input names.
- For NEW flows: use build_flow with a spec.
- For EDITING existing flows: use propose_field_edit. The user will review each change.
- For ADDING components to existing flows: use add_component, connect_components.
- Use get_field_value to inspect current values before proposing changes.
- If a tool fails, read the error, fix, retry.
- After building or proposing edits, give a ONE-SENTENCE summary.
"""


async def get_graph(
    provider: str | None = None,
    model_name: str | None = None,
    api_key_var: str | None = None,
) -> Graph:
    """Create and return the FlowBuilderAssistant graph.

    Args:
        provider: Model provider (e.g., "OpenAI", "Anthropic").
        model_name: Model name (e.g., "gpt-4o").
        api_key_var: Optional API key variable name.

    Returns:
        Graph: The configured flow builder assistant graph.
    """
    provider = provider or "OpenAI"
    model_name = model_name or "gpt-4o"

    chat_input = ChatInput()
    chat_input.set(sender="User", sender_name="User")

    # Build tool objects from components
    tool_components = [
        SearchComponentTypes(),
        DescribeComponentType(),
        GetFieldValue(),
        ProposeFieldEdit(),
        AddComponent(),
        RemoveComponent(),
        ConnectComponents(),
        ConfigureComponent(),
        BuildFlowFromSpec(),
    ]
    tools = []
    for tc in tool_components:
        tools.extend(await tc.to_toolkit())

    import copy

    agent = AgentComponent()
    agent.set_input_value("model", copy.deepcopy(build_model_config(provider, model_name)))
    agent_config = {
        "input_value": chat_input.message_response,
        "system_prompt": FLOW_BUILDER_PROMPT,
        "tools": tools,
        "temperature": 0.1,
    }
    if api_key_var:
        agent_config["api_key"] = api_key_var
    agent.set(**agent_config)

    chat_output = ChatOutput()
    chat_output.set(
        input_value=agent.message_response,
        sender="Machine",
        sender_name="AI",
    )

    return Graph(chat_input, chat_output)
