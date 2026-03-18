# watsonx Orchestrate Integration - Testing Guide

## Quick Test (Without watsonx Orchestrate CLI)

You can test the integration **right now** without installing watsonx Orchestrate CLI by testing the API endpoints directly.

### Test 1: Verify MCP Server is Running

```bash
# This should return a "Not Acceptable" error - that's GOOD!
# It means the MCP server is running and waiting for proper MCP clients
curl -v http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
```

**Expected Output:**

```json
{
  "jsonrpc": "2.0",
  "id": "server-error",
  "error": {
    "code": -32600,
    "message": "Not Acceptable: Client must accept text/event-stream"
  }
}
```

✅ **This error is CORRECT** - it confirms the MCP server is working!

### Test 2: List Your MCP-Enabled Tools

```bash
# Get list of all tools available via MCP
curl -s "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270?mcp_enabled=true" \
  -H "Accept: application/json" | python3 -m json.tool | head -30
```

**Expected Output:**

```json
{
    "tools": [
        {
            "id": "d1a37f1b-beac-42d8-9e70-c903ed70d09f",
            "mcp_enabled": true,
            "action_name": "basic_prompting",
            "action_description": "Perform basic prompting with an OpenAI model.",
            "name": "Basic Prompting",
            "description": "Perform basic prompting with an OpenAI model."
        },
        ...
    ]
}
```

✅ **Success:** You should see 62 tools listed

### Test 3: Export watsonx Orchestrate Configuration

```bash
# Generate the complete export
curl -s "http://localhost:7860/api/v1/wxo/32b1f197-4565-4ad9-a214-29bc05ae0270/export" \
  -H "Accept: application/json" | python3 -m json.tool | head -50
```

**Expected Output:**

```json
{
    "project_id": "32b1f197-4565-4ad9-a214-29bc05ae0270",
    "project_name": "Starter Project",
    "toolkit_config": {
        "toolkit_name": "starter_project",
        "toolkit_type": "mcp",
        "mcp_url": "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable",
        "tools": [...]
    },
    "cli_import_command": "orchestrate toolkits add ...",
    "agent_yaml": "apiVersion: orchestrate.ibm.com/v1...",
    ...
}
```

✅ **Success:** You should see complete configuration with toolkit, agent, and commands

### Test 4: Get Agent YAML

```bash
# Get just the agent configuration
curl -s "http://localhost:7860/api/v1/wxo/32b1f197-4565-4ad9-a214-29bc05ae0270/export/agent-yaml"
```

**Expected Output:**

```yaml
apiVersion: orchestrate.ibm.com/v1
kind: Agent
metadata:
  name: starter_project_agent
spec:
  description: AI agent powered by Starter Project Langflow project
  tools:
    - basic_prompting
    - document_qa
    ...
```

✅ **Success:** You should see valid YAML configuration

### Test 5: Verify Export Files

```bash
# Check that the export script created all files
ls -lh wxo_export/
```

**Expected Output:**

```
-rw-r--r--  agent.yaml
-rw-r--r--  full_export.json
-rwxr-xr-x  import_toolkit.sh
-rw-r--r--  SETUP_INSTRUCTIONS.md
-rw-r--r--  toolkit_config.json
```

✅ **Success:** All 5 files should exist

## Full Integration Test (With watsonx Orchestrate CLI)

### Prerequisites

1. **Install watsonx Orchestrate CLI**
   - Follow IBM documentation: https://www.ibm.com/docs/en/watsonx-orchestrate
   - Or contact your IBM representative

2. **Authenticate**

   ```bash
   orchestrate login
   ```

3. **Verify Installation**
   ```bash
   orchestrate --version
   ```

### Step-by-Step Integration Test

#### Step 1: Import Toolkit

```bash
# Import your Langflow tools as a toolkit
./wxo_export/import_toolkit.sh
```

**Expected Output:**

```
✓ Toolkit 'starter_project' imported successfully
```

**Verify:**

```bash
orchestrate toolkits list
```

You should see `starter_project` in the list.

#### Step 2: Inspect Toolkit

```bash
# See all 62 tools
orchestrate toolkits describe starter_project
```

**Expected Output:**

```
Name: starter_project
Type: mcp
URL: http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
Tools:
  - basic_prompting: Perform basic prompting with an OpenAI model.
  - document_qa: Integrates PDF reading with a language model...
  - simple_agent: A simple but powerful starter agent.
  ... (59 more tools)
```

✅ **Success:** All 62 tools should be listed

#### Step 3: Test Individual Tool

```bash
# Test calling a single tool directly
orchestrate tools run starter_project.basic_prompting \
  --input '{"prompt": "Hello, what is 2+2?"}'
```

**Expected Output:**

```json
{
  "result": "2+2 equals 4."
}
```

✅ **Success:** Tool executes and returns a response

#### Step 4: Create Agent

```bash
# Create an agent that uses your tools
orchestrate agents create -f wxo_export/agent.yaml
```

**Expected Output:**

```
✓ Agent 'starter_project_agent' created successfully
```

**Verify:**

```bash
orchestrate agents list
```

You should see `starter_project_agent` in the list.

#### Step 5: Test Agent

```bash
# Run your agent with a simple prompt
orchestrate agents run starter_project_agent \
  --prompt "What tools do you have access to?"
```

**Expected Output:**

```
I have access to 62 tools from the Starter Project, including:
- basic_prompting: For OpenAI model interactions
- document_qa: For PDF question answering
- simple_agent: A starter agent
... and 59 more tools for various AI tasks.
```

✅ **Success:** Agent responds with tool information

#### Step 6: Test Agent with Tool Usage

```bash
# Ask the agent to use a specific tool
orchestrate agents run starter_project_agent \
  --prompt "Use the basic_prompting tool to tell me a joke"
```

**Expected Output:**

```
[Agent uses basic_prompting tool]
Why did the AI go to therapy? Because it had too many neural networks!
```

✅ **Success:** Agent successfully calls Langflow tool and returns result

#### Step 7: Test Document Q&A Tool

```bash
# Test the document_qa tool
orchestrate agents run starter_project_agent \
  --prompt "Can you help me analyze a PDF document?"
```

**Expected Output:**

```
Yes! I can help you analyze PDF documents using the document_qa tool.
Please provide the PDF file or URL, and let me know what questions you have about it.
```

✅ **Success:** Agent recognizes document capabilities

## Troubleshooting Tests

### Test: MCP Server Connectivity

```bash
# Test if MCP server is reachable
curl -I http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
```

**Expected:** HTTP 200 or 406 (Not Acceptable)
**Problem if:** Connection refused or timeout

**Fix:**

```bash
# Restart Langflow
make run_cli
```

### Test: Tool Discovery

```bash
# Count how many tools are available
curl -s "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270?mcp_enabled=true" \
  -H "Accept: application/json" | python3 -c "import json, sys; print(len(json.load(sys.stdin)['tools']))"
```

**Expected:** 62
**Problem if:** 0 or fewer than expected

**Fix:**

```bash
# Enable MCP for flows in Langflow UI
# Go to each flow → Settings → Enable MCP
```

### Test: Export API

```bash
# Test all export endpoints
for endpoint in export export/toolkit-config export/agent-yaml export/setup-script; do
  echo "Testing: $endpoint"
  curl -s -o /dev/null -w "%{http_code}\n" \
    "http://localhost:7860/api/v1/wxo/32b1f197-4565-4ad9-a214-29bc05ae0270/$endpoint"
done
```

**Expected:** All return 200
**Problem if:** Any return 404 or 500

**Fix:**

```bash
# Restart Langflow to reload API routes
make run_clic
```

## Performance Tests

### Test: Export Speed

```bash
# Measure export time
time curl -s "http://localhost:7860/api/v1/wxo/32b1f197-4565-4ad9-a214-29bc05ae0270/export" \
  -o /dev/null
```

**Expected:** < 2 seconds
**Problem if:** > 5 seconds

### Test: Tool Listing Speed

```bash
# Measure tool listing time
time curl -s "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270?mcp_enabled=true" \
  -o /dev/null
```

**Expected:** < 1 second
**Problem if:** > 3 seconds

## Automated Test Script

Save this as `test_wxo_integration.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Testing watsonx Orchestrate Integration"
echo ""

# Test 1: MCP Server
echo "Test 1: MCP Server..."
if curl -s -f http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable > /dev/null 2>&1 || [ $? -eq 22 ]; then
  echo "✅ MCP Server is running"
else
  echo "❌ MCP Server is not responding"
  exit 1
fi

# Test 2: Tool Count
echo "Test 2: Tool Count..."
TOOL_COUNT=$(curl -s "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270?mcp_enabled=true" \
  -H "Accept: application/json" | python3 -c "import json, sys; print(len(json.load(sys.stdin)['tools']))")
if [ "$TOOL_COUNT" -eq 62 ]; then
  echo "✅ All 62 tools available"
else
  echo "❌ Expected 62 tools, found $TOOL_COUNT"
  exit 1
fi

# Test 3: Export API
echo "Test 3: Export API..."
if curl -s -f "http://localhost:7860/api/v1/wxo/32b1f197-4565-4ad9-a214-29bc05ae0270/export" > /dev/null; then
  echo "✅ Export API working"
else
  echo "❌ Export API failed"
  exit 1
fi

# Test 4: Export Files
echo "Test 4: Export Files..."
if [ -f "wxo_export/agent.yaml" ] && [ -f "wxo_export/import_toolkit.sh" ]; then
  echo "✅ Export files exist"
else
  echo "❌ Export files missing"
  exit 1
fi

echo ""
echo "🎉 All tests passed!"
echo ""
echo "Next steps:"
echo "1. Install watsonx Orchestrate CLI"
echo "2. Run: ./wxo_export/import_toolkit.sh"
echo "3. Run: orchestrate agents create -f wxo_export/agent.yaml"
echo "4. Run: orchestrate agents run starter_project_agent --prompt 'Hello!'"
```

Run it:

```bash
chmod +x test_wxo_integration.sh
./test_wxo_integration.sh
```

## Success Criteria

✅ **Integration is working if:**

1. MCP server responds (even with "Not Acceptable" error)
2. 62 tools are listed in the API
3. Export generates valid JSON and YAML
4. Export files exist in `wxo_export/`
5. (With CLI) Toolkit imports successfully
6. (With CLI) Agent can be created
7. (With CLI) Agent can execute tools

## Next Steps After Testing

Once all tests pass:

1. **Share with team:** Send them the `wxo_export/` folder
2. **Deploy to production:** Use production Langflow URL in export
3. **Create more agents:** Customize `agent.yaml` for different use cases
4. **Monitor usage:** Check watsonx Orchestrate logs
5. **Iterate:** Add more flows in Langflow, re-export, update toolkit

## Support

If tests fail, check:

- Langflow is running: `curl http://localhost:7860/health`
- Project ID is correct: `32b1f197-4565-4ad9-a214-29bc05ae0270`
- Flows have MCP enabled in Langflow UI
- watsonx Orchestrate CLI is authenticated

For help, review:

- `docs/WATSONX_ORCHESTRATE_INTEGRATION_COMPLETE.md`
- `wxo_export/SETUP_INSTRUCTIONS.md`
- Langflow logs: Check terminal where Langflow is running
