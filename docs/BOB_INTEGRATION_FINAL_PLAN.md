# IBM watsonx Orchestrate (Bob) Integration - FINAL PLAN

## Based on IBM Tutorial Analysis

## 🎯 Perfect Match: Langflow MCP ↔ watsonx Orchestrate

After analyzing the IBM tutorial, the integration is **even simpler** than expected. The tutorial shows that watsonx Orchestrate uses the **exact same MCP protocol** that Langflow already implements!

## Key Insights from IBM Tutorial

### What the Tutorial Shows

1. **Bob creates MCP tools** using FastMCP
2. **MCP tools are imported** into watsonx Orchestrate using CLI: `orchestrate toolkits`
3. **Agents use MCP tools** through standard MCP protocol
4. **MCP servers connect** via `mcp-proxy` with streamable HTTP

### What This Means for Langflow

**Langflow flows ARE MCP tools!** We don't need to create anything new. We just need to:

1. Import Langflow's MCP server into watsonx Orchestrate
2. Langflow flows automatically become watsonx Orchestrate tools
3. Create agents in watsonx Orchestrate that use these tools

## The Integration Architecture (From Tutorial)

```
┌─────────────────────────────────────────────────────────────┐
│                  watsonx Orchestrate                         │
│  • Agents (created via YAML or CLI)                         │
│  • Uses MCP tools for reasoning                             │
│  • Connects to MCP servers                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ MCP Protocol
                         │ (via mcp-proxy)
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Langflow MCP Server                             │
│  • Already running at /api/v1/mcp/project/{id}/streamable  │
│  • Exposes flows as MCP tools                               │
│  • Handles tool execution                                   │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Integration (Based on Tutorial)

### Step 1: Start Langflow MCP Server (Already Done!)

Langflow's MCP server is already running when you start Langflow:

- **Global MCP**: `http://localhost:7860/api/v1/mcp/streamable`
- **Project MCP**: `http://localhost:7860/api/v1/mcp/project/{project_id}/streamable`

### Step 2: Import Langflow MCP Tools into watsonx Orchestrate

Using the watsonx Orchestrate CLI (from tutorial):

```bash
# Add Langflow MCP server to watsonx Orchestrate
orchestrate toolkits add \
  --name "langflow-tools" \
  --type mcp \
  --command "uvx" \
  --args "mcp-proxy --transport streamablehttp http://localhost:7860/api/v1/mcp/project/{project_id}/streamable"
```

Or using MCP configuration file:

```json
{
  "mcpServers": {
    "langflow-tools": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "--transport",
        "streamablehttp",
        "http://localhost:7860/api/v1/mcp/project/{project_id}/streamable"
      ],
      "env": {
        "LANGFLOW_API_KEY": "sk-..."
      }
    }
  }
}
```

### Step 3: Create Agent in watsonx Orchestrate

Create agent YAML file (from tutorial):

```yaml
name: customer_support_agent
description: Handles customer inquiries using Langflow tools
llm:
  provider: groq
  model: openai/gpt-oss-120b
tools:
  - langflow-tools.customer_lookup
  - langflow-tools.ticket_creation
  - langflow-tools.knowledge_search
```

Import agent:

```bash
orchestrate agents import customer_support_agent.yaml
```

### Step 4: Test Agent

```bash
# List agents
orchestrate agents list

# Test agent
orchestrate agents test customer_support_agent \
  --input "Why is order 456 delayed?"
```

## What We Need to Build

### Option 1: Manual Setup (Works Today!)

**Documentation only** - Users can connect Langflow to watsonx Orchestrate right now:

1. **User Guide**: "Connect Langflow to watsonx Orchestrate"
   - How to get Langflow MCP URL
   - How to add to watsonx Orchestrate
   - How to create agents

2. **Example Flows**: Pre-built flows that work as watsonx Orchestrate tools

**Timeline**: 1 week (documentation only)

### Option 2: Automated Setup (Recommended)

**Add automation helpers** to make it one-click:

#### Backend Helper

```python
# src/backend/base/langflow/api/v1/wxo_integration.py

@router.post("/wxo/export/{project_id}")
async def export_for_watsonx_orchestrate(
    project_id: UUID,
    current_user: CurrentActiveUser,
):
    """Generate watsonx Orchestrate configuration for Langflow MCP server."""

    # Get existing MCP URL (already implemented)
    mcp_url = await get_project_streamable_http_url(project_id)

    # Generate API key if needed
    api_key = await create_api_key(session, ApiKeyCreate(
        name=f"watsonx Orchestrate - {project.name}"
    ), current_user.id)

    # Return watsonx Orchestrate config
    return {
        "mcp_config": {
            "mcpServers": {
                f"langflow-{project.name}": {
                    "command": "uvx",
                    "args": [
                        "mcp-proxy",
                        "--transport", "streamablehttp",
                        mcp_url
                    ],
                    "env": {
                        "LANGFLOW_API_KEY": api_key
                    }
                }
            }
        },
        "cli_command": f"orchestrate toolkits add --name langflow-{project.name} --type mcp --url {mcp_url}",
        "instructions": "Copy the MCP config above and add it to your watsonx Orchestrate configuration"
    }
```

#### Frontend UI

```typescript
// src/frontend/src/components/wxo/export-to-wxo-button.tsx

export function ExportToWatsonxOrchestrate({ projectId }: Props) {
  const handleExport = async () => {
    const config = await exportForWXO(projectId);

    // Show modal with:
    // 1. MCP configuration (copy to clipboard)
    // 2. CLI command (copy to clipboard)
    // 3. Step-by-step instructions

    showModal({
      title: "Export to watsonx Orchestrate",
      content: (
        <>
          <h3>MCP Configuration</h3>
          <CodeBlock copyable>{config.mcp_config}</CodeBlock>

          <h3>CLI Command</h3>
          <CodeBlock copyable>{config.cli_command}</CodeBlock>

          <h3>Instructions</h3>
          <ol>
            <li>Copy the MCP configuration above</li>
            <li>Add it to your watsonx Orchestrate MCP config</li>
            <li>Or run the CLI command</li>
            <li>Create an agent that uses these tools</li>
          </ol>
        </>
      )
    });
  };

  return (
    <Button onClick={handleExport}>
      <WatsonxIcon />
      Export to watsonx Orchestrate
    </Button>
  );
}
```

**Timeline**: 2 weeks (backend + frontend + docs)

### Option 3: Full Integration (Future)

**Direct watsonx Orchestrate API integration**:

- Automatic toolkit registration
- Agent creation from Langflow UI
- Real-time sync
- Deployment monitoring

**Timeline**: 4-6 weeks (requires watsonx Orchestrate API access)

## Implementation Plan

### Week 1: Documentation & Validation

**Goal**: Prove it works manually

- [ ] Write "Connect Langflow to watsonx Orchestrate" guide
- [ ] Test manual connection with watsonx Orchestrate
- [ ] Create example flows
- [ ] Document common issues

**Deliverable**: Working manual integration + documentation

### Week 2: Configuration Helper (Backend)

**Goal**: Auto-generate watsonx Orchestrate config

- [ ] Create `/api/v1/wxo/export/{project_id}` endpoint
- [ ] Generate MCP configuration
- [ ] Generate CLI commands
- [ ] Add API key management

**Deliverable**: API endpoint that generates watsonx Orchestrate config

### Week 3: UI (Frontend)

**Goal**: One-click export

- [ ] Add "Export to watsonx Orchestrate" button
- [ ] Create export modal with instructions
- [ ] Add copy-to-clipboard functionality
- [ ] Show connection status

**Deliverable**: UI for exporting to watsonx Orchestrate

### Week 4: Testing & Polish

**Goal**: Production-ready

- [ ] Test with real watsonx Orchestrate instance
- [ ] Create video tutorial
- [ ] Add troubleshooting guide
- [ ] User acceptance testing

**Deliverable**: Production-ready integration

## Files to Create/Modify

### New Files

```
Backend:
src/backend/base/langflow/api/v1/wxo_integration.py  (~150 lines)

Frontend:
src/frontend/src/components/wxo/export-to-wxo-button.tsx  (~100 lines)
src/frontend/src/modals/WXOExportModal/index.tsx  (~200 lines)

Documentation:
docs/guides/connect-to-watsonx-orchestrate.md
docs/examples/wxo-customer-support-agent.md
docs/troubleshooting/wxo-common-issues.md
```

### Modified Files

```
src/backend/base/langflow/api/router.py
  - Add wxo_integration router

src/frontend/src/components/core/flowToolbar/index.tsx
  - Add "Export to watsonx Orchestrate" button
```

## Example Use Case (From Tutorial)

### Factorial Agent (Tutorial Example)

The tutorial creates a factorial agent with two MCP tools. Here's how it would work with Langflow:

#### 1. Create Flows in Langflow

**Flow 1: Calculate Factorial Value**

```
Input (number) → Python Code (factorial calculation) → Output (result)
```

**Flow 2: Count Factorial Digits**

```
Input (number) → Python Code (count digits) → Output (digit count)
```

#### 2. Enable MCP for Flows

In Langflow UI:

- Enable "MCP Enabled" for both flows
- Set action names: `factorial_value`, `factorial_digits`
- Set descriptions

#### 3. Export to watsonx Orchestrate

Click "Export to watsonx Orchestrate" button:

- Generates MCP configuration
- Creates CLI command
- Shows instructions

#### 4. Create Agent in watsonx Orchestrate

```yaml
name: factorial_agent
description: Calculates factorials and digit counts
llm:
  provider: groq
  model: openai/gpt-oss-120b
tools:
  - langflow-tools.factorial_value
  - langflow-tools.factorial_digits
```

#### 5. Test Agent

```bash
orchestrate agents test factorial_agent \
  --input "What is the factorial value of 5?"
```

Agent calls `langflow-tools.factorial_value` → Langflow executes flow → Returns 120

## Key Differences from Original Plan

### Original Plan (Before Tutorial)

- Build custom Bob API client
- Create Bob-specific skill format
- Implement translation layer
- **12 weeks of development**

### Revised Plan (After MCP Discovery)

- Reuse existing MCP infrastructure
- Add configuration helpers
- **4 weeks of development**

### Final Plan (After Tutorial Analysis)

- **Langflow already works with watsonx Orchestrate!**
- Just need documentation and UI helpers
- **2 weeks for automation, or 1 week for docs only**

## Success Metrics

After implementation, users should be able to:

✅ Export Langflow project to watsonx Orchestrate in < 2 minutes
✅ See Langflow flows as watsonx Orchestrate tools
✅ Create agents that use Langflow tools
✅ Execute flows from watsonx Orchestrate
✅ Monitor execution in Langflow

## Comparison: Tutorial vs Langflow

| Tutorial Step                 | Langflow Equivalent              | Status            |
| ----------------------------- | -------------------------------- | ----------------- |
| Create MCP server             | Langflow MCP server              | ✅ Already exists |
| Build MCP tools               | Create Langflow flows            | ✅ Already exists |
| Test MCP tools                | Test flows in Langflow           | ✅ Already exists |
| Import to watsonx Orchestrate | Export MCP config                | 🔨 Need to build  |
| Create agent                  | Use watsonx Orchestrate CLI      | ✅ Works today    |
| Test agent                    | Execute from watsonx Orchestrate | ✅ Works today    |

## Recommended Approach

### Phase 1: Quick Win (1 week) - START HERE

**Goal**: Prove it works

1. Write documentation on connecting Langflow to watsonx Orchestrate
2. Test manual connection
3. Create example flows
4. Share with users

**Outcome**: Users can connect Langflow to watsonx Orchestrate today

### Phase 2: Automation (2 weeks)

**Goal**: Make it easy

1. Build configuration generator API
2. Create export UI
3. Add copy-to-clipboard
4. Video tutorial

**Outcome**: One-click export to watsonx Orchestrate

### Phase 3: Advanced (Future)

**Goal**: Full integration

1. Direct watsonx Orchestrate API integration
2. Agent creation from Langflow
3. Real-time sync
4. Monitoring dashboard

**Outcome**: Seamless Langflow ↔ watsonx Orchestrate integration

## Next Steps

1. **Validate with watsonx Orchestrate team**
   - Confirm MCP protocol compatibility
   - Get access to test instance
   - Understand any watsonx Orchestrate-specific requirements

2. **Create documentation** (Week 1)
   - Manual connection guide
   - Example flows
   - Troubleshooting

3. **Build automation** (Weeks 2-3)
   - Configuration generator
   - Export UI
   - Testing

4. **Launch** (Week 4)
   - User testing
   - Video tutorial
   - Announcement

## Summary

**The integration is simpler than we thought!**

- ✅ Langflow already has MCP server
- ✅ Flows are already MCP tools
- ✅ watsonx Orchestrate uses MCP protocol
- ✅ Connection works today (manually)
- 🔨 Just need automation and documentation

**Timeline**: 2 weeks for full automation, or 1 week for documentation only

**Effort**: Minimal - mostly configuration and UI work

**Impact**: Huge - Langflow becomes a visual tool builder for watsonx Orchestrate agents!

---

**Ready to start?** I recommend beginning with Phase 1 (documentation) to validate the integration, then moving to Phase 2 (automation) to make it user-friendly.
