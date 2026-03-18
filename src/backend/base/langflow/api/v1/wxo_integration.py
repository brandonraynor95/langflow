"""IBM watsonx Orchestrate (Bob) Integration API.

This module provides endpoints for exporting Langflow projects and flows
as watsonx Orchestrate skills and agent configurations.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.api.utils import CurrentActiveMCPUser
from langflow.services.database.models import Flow, Folder
from langflow.services.deps import session_scope
from lfx.base.mcp.util import sanitize_mcp_name

router = APIRouter(prefix="/wxo", tags=["watsonx_orchestrate"])


class WXOToolConfig(BaseModel):
    """Configuration for a single watsonx Orchestrate tool."""

    name: str = Field(..., description="Tool name (sanitized for MCP)")
    description: str = Field(..., description="Tool description")
    flow_id: str = Field(..., description="Langflow flow ID")
    mcp_enabled: bool = Field(..., description="Whether MCP is enabled for this flow")


class WXOToolkitConfig(BaseModel):
    """Configuration for watsonx Orchestrate toolkit import."""

    toolkit_name: str = Field(..., description="Name of the toolkit")
    toolkit_type: str = Field(default="mcp", description="Toolkit type (always 'mcp')")
    mcp_url: str = Field(..., description="MCP server URL")
    tools: list[WXOToolConfig] = Field(..., description="List of tools in the toolkit")


class WXOAgentConfig(BaseModel):
    """Configuration for a watsonx Orchestrate agent."""

    agent_name: str = Field(..., description="Name of the agent")
    agent_description: str = Field(..., description="Description of the agent")
    tools: list[str] = Field(..., description="List of tool names the agent can use")
    system_prompt: str | None = Field(None, description="Optional system prompt for the agent")


class WXOExportResponse(BaseModel):
    """Response containing watsonx Orchestrate export configurations."""

    project_id: str = Field(..., description="Langflow project ID")
    project_name: str = Field(..., description="Langflow project name")
    toolkit_config: WXOToolkitConfig = Field(..., description="Toolkit configuration")
    cli_import_command: str = Field(..., description="CLI command to import the toolkit")
    agent_yaml: str = Field(..., description="YAML configuration for creating an agent")
    agent_import_command: str = Field(..., description="CLI command to import the agent")
    setup_instructions: str = Field(..., description="Step-by-step setup instructions")


@router.get("/{project_id}/export")
async def export_project_to_wxo(
    project_id: UUID,
    current_user: CurrentActiveMCPUser,
    base_url: str = "http://localhost:7860",
) -> Response:
    """Export a Langflow project as watsonx Orchestrate configuration.

    This endpoint generates all necessary configuration files and commands
    to import a Langflow project into IBM watsonx Orchestrate as a toolkit
    and create agents that use the project's flows.

    Args:
        project_id: UUID of the Langflow project to export
        current_user: Authenticated user
        base_url: Base URL of the Langflow instance (default: http://localhost:7860)

    Returns:
        JSON response with toolkit config, agent YAML, and CLI commands
    """
    try:
        async with session_scope() as session:
            # Fetch the project
            project = (
                await session.exec(
                    select(Folder).where(Folder.id == project_id, Folder.user_id == current_user.id)
                )
            ).first()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Query MCP-enabled flows in the project
            flows_query = select(Flow).where(
                Flow.folder_id == project_id, Flow.is_component == False, Flow.mcp_enabled == True  # noqa: E712
            )
            flows = (await session.exec(flows_query)).all()

            if not flows:
                raise HTTPException(
                    status_code=400,
                    detail="No MCP-enabled flows found in this project. Enable MCP for at least one flow.",
                )

            # Build tool configurations
            tools = []
            tool_names = []
            for flow in flows:
                if flow.user_id is None:
                    continue

                # Use action_name if available, otherwise sanitize flow name
                tool_name = sanitize_mcp_name(flow.action_name) if flow.action_name else sanitize_mcp_name(flow.name)
                tool_description = flow.action_description or (
                    flow.description if flow.description else f"Tool generated from flow: {flow.name}"
                )

                tools.append(
                    WXOToolConfig(
                        name=tool_name,
                        description=tool_description,
                        flow_id=str(flow.id),
                        mcp_enabled=bool(flow.mcp_enabled),
                    )
                )
                tool_names.append(tool_name)

            # Generate MCP URL
            mcp_url = f"{base_url}/api/v1/mcp/project/{project_id}/streamable"

            # Sanitize project name for toolkit
            toolkit_name = sanitize_mcp_name(project.name)

            # Build toolkit configuration
            toolkit_config = WXOToolkitConfig(
                toolkit_name=toolkit_name, toolkit_type="mcp", mcp_url=mcp_url, tools=tools
            )

            # Generate CLI import command
            cli_import_command = f"""orchestrate toolkits add \\
  --name {toolkit_name} \\
  --type mcp \\
  --url {mcp_url}"""

            # Generate agent YAML
            agent_name = f"{toolkit_name}_agent"
            agent_description = f"AI agent powered by {project.name} Langflow project"

            agent_yaml = f"""apiVersion: orchestrate.ibm.com/v1
kind: Agent
metadata:
  name: {agent_name}
spec:
  description: {agent_description}
  tools:
{chr(10).join(f'    - {tool_name}' for tool_name in tool_names)}
  systemPrompt: |
    You are an AI assistant with access to the following tools from the {project.name} project:
    {chr(10).join(f'    - {tool.name}: {tool.description}' for tool in tools)}
    
    Use these tools to help users accomplish their tasks.
    Always explain what you're doing and ask for clarification when needed.
"""

            # Generate agent import command
            agent_import_command = f"""# Save the YAML above to a file (e.g., {agent_name}.yaml), then run:
orchestrate agents create -f {agent_name}.yaml"""

            # Generate setup instructions
            setup_instructions = f"""# watsonx Orchestrate Integration Setup

## Prerequisites
1. Install watsonx Orchestrate CLI: https://www.ibm.com/docs/en/watsonx-orchestrate
2. Authenticate: `orchestrate login`
3. Ensure Langflow is running at {base_url}

## Step 1: Import Toolkit
Run this command to import all {len(tools)} tools from the "{project.name}" project:

```bash
{cli_import_command}
```

## Step 2: Verify Toolkit
```bash
orchestrate toolkits list
orchestrate toolkits describe {toolkit_name}
```

## Step 3: Create Agent
Save the agent YAML configuration to a file (e.g., `{agent_name}.yaml`), then:

```bash
orchestrate agents create -f {agent_name}.yaml
```

## Step 4: Test Agent
```bash
orchestrate agents run {agent_name} --prompt "Hello, what can you help me with?"
```

## Available Tools
{chr(10).join(f'{i+1}. **{tool.name}**: {tool.description}' for i, tool in enumerate(tools))}

## Next Steps
- Customize the agent's system prompt in the YAML file
- Add more flows to your Langflow project and re-export
- Create multiple agents with different tool combinations
- Deploy agents to production watsonx Orchestrate environment

## Troubleshooting
- If toolkit import fails, verify Langflow is accessible at {mcp_url}
- Check that all flows have MCP enabled in Langflow UI
- Ensure watsonx Orchestrate CLI is properly authenticated
"""

            response = WXOExportResponse(
                project_id=str(project_id),
                project_name=project.name,
                toolkit_config=toolkit_config,
                cli_import_command=cli_import_command,
                agent_yaml=agent_yaml,
                agent_import_command=agent_import_command,
                setup_instructions=setup_instructions,
            )

            return JSONResponse(content=response.model_dump(mode="json"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting to watsonx Orchestrate: {e!s}") from e


@router.get("/{project_id}/export/toolkit-config")
async def export_toolkit_config(
    project_id: UUID,
    current_user: CurrentActiveMCPUser,
    base_url: str = "http://localhost:7860",
) -> Response:
    """Export just the toolkit configuration JSON.

    Useful for programmatic integration or custom import scripts.
    """
    full_export = await export_project_to_wxo(project_id, current_user, base_url)
    body_bytes = full_export.body if isinstance(full_export.body, bytes) else str(full_export.body).encode("utf-8")
    data = json.loads(body_bytes.decode("utf-8"))
    return JSONResponse(content=data["toolkit_config"])


@router.get("/{project_id}/export/agent-yaml")
async def export_agent_yaml(
    project_id: UUID,
    current_user: CurrentActiveMCPUser,
    base_url: str = "http://localhost:7860",
) -> Response:
    """Export just the agent YAML configuration.

    Returns plain text YAML that can be saved directly to a file.
    """
    full_export = await export_project_to_wxo(project_id, current_user, base_url)
    body_bytes = full_export.body if isinstance(full_export.body, bytes) else str(full_export.body).encode("utf-8")
    data = json.loads(body_bytes.decode("utf-8"))
    return Response(content=data["agent_yaml"], media_type="text/yaml")


@router.get("/{project_id}/export/setup-script")
async def export_setup_script(
    project_id: UUID,
    current_user: CurrentActiveMCPUser,
    base_url: str = "http://localhost:7860",
) -> Response:
    """Export a complete bash setup script.

    This script automates the entire integration process.
    """
    full_export = await export_project_to_wxo(project_id, current_user, base_url)
    body_bytes = full_export.body if isinstance(full_export.body, bytes) else str(full_export.body).encode("utf-8")
    data = json.loads(body_bytes.decode("utf-8"))

    script = f"""#!/bin/bash
# watsonx Orchestrate Integration Setup Script
# Generated for project: {data['project_name']}

set -e

echo "========================================="
echo "watsonx Orchestrate Integration Setup"
echo "Project: {data['project_name']}"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v orchestrate &> /dev/null; then
    echo "ERROR: watsonx Orchestrate CLI not found"
    echo "Install from: https://www.ibm.com/docs/en/watsonx-orchestrate"
    exit 1
fi

echo "✓ watsonx Orchestrate CLI found"
echo ""

# Import toolkit
echo "Step 1: Importing toolkit..."
{data['cli_import_command']}
echo "✓ Toolkit imported successfully"
echo ""

# Create agent YAML file
AGENT_FILE="{data['project_name']}_agent.yaml"
echo "Step 2: Creating agent configuration..."
cat > "$AGENT_FILE" << 'EOF'
{data['agent_yaml']}
EOF
echo "✓ Agent configuration saved to $AGENT_FILE"
echo ""

# Import agent
echo "Step 3: Creating agent..."
orchestrate agents create -f "$AGENT_FILE"
echo "✓ Agent created successfully"
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Test your agent with:"
echo "  orchestrate agents run {data['project_name']}_agent --prompt 'Hello!'"
echo ""
"""

    return Response(content=script, media_type="text/x-shellscript")

# Made with Bob
