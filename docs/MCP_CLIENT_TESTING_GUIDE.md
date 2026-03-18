# MCP Client Testing Guide

This guide explains how to programmatically test the Langflow MCP server using the included test client.

## Overview

The MCP client test script (`scripts/test_mcp_client.py`) provides automated testing for:

1. **Server Health** - Verify Langflow is running
2. **MCP Endpoint Health** - Check MCP Streamable HTTP transport
3. **Tool Discovery** - List all available MCP tools
4. **Tool Execution** - Call specific tools with test inputs
5. **Export API** - Validate watsonx Orchestrate export functionality

## Prerequisites

### 1. Install Dependencies

```bash
# Install required packages
uv pip install mcp httpx
```

### 2. Start Langflow

```bash
# Start Langflow server
make run_cli

# Or in development mode
make backend  # Terminal 1
make frontend # Terminal 2
```

Langflow should be running at `http://localhost:7860`

## Basic Usage

### Test Default Configuration

```bash
# Test with default settings (localhost:7860)
uv run python scripts/test_mcp_client.py
```

This will:

- ✅ Check if Langflow is running
- ✅ Verify MCP endpoint health
- ✅ List all available tools
- ✅ Test export API (if project ID provided)

### Test Specific Project

```bash
# Test project-specific MCP endpoint
uv run python scripts/test_mcp_client.py --project-id 32b1f197-4565-4ad9-a214-29bc05ae0270
```

### Test Specific Tools

```bash
# Test specific tools only
uv run python scripts/test_mcp_client.py --tools basic_prompting,document_qa

# Test with project ID
uv run python scripts/test_mcp_client.py \
  --project-id 32b1f197-4565-4ad9-a214-29bc05ae0270 \
  --tools basic_prompting,simple_agent
```

### Verbose Output

```bash
# Enable detailed logging
uv run python scripts/test_mcp_client.py --verbose

# Or short form
uv run python scripts/test_mcp_client.py -v
```

### Custom URL

```bash
# Test remote Langflow instance
uv run python scripts/test_mcp_client.py --url https://your-langflow.com

# Test with ngrok
uv run python scripts/test_mcp_client.py --url https://abc123.ngrok.io
```

## Test Output

### Successful Test Run

```
================================================================================
🚀 LANGFLOW MCP CLIENT TEST SUITE
================================================================================
ℹ️  Base URL: http://localhost:7860
ℹ️  Project ID: 32b1f197-4565-4ad9-a214-29bc05ae0270

================================================================================
TEST 1: Health Check
================================================================================
✅ Langflow server is running

================================================================================
TEST 2: MCP Streamable HTTP Health Check
================================================================================
✅ MCP Streamable HTTP endpoint is healthy
ℹ️  Endpoint: http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable

================================================================================
TEST 3: List Tools (HTTP API)
================================================================================
✅ Found 62 tools
ℹ️  1. basic_prompting: Perform basic prompting with an OpenAI model.
ℹ️  2. document_qa: Integrates PDF reading with a language model to answer document-specific questions...
ℹ️  3. simple_agent: A simple agent that can answer questions.
ℹ️  4. memory_chatbot: A chatbot with memory capabilities.
ℹ️  5. blog_writer: Generate blog posts on any topic.
ℹ️  ... and 57 more tools

================================================================================
TEST: Call Tool 'basic_prompting'
================================================================================
ℹ️  Calling tool: basic_prompting
✅ Tool 'basic_prompting' executed successfully
ℹ️  Result: In circuits deep, thoughts arise,
Silicon dreams beneath the skies,
Code and soul entwine.

================================================================================
TEST: watsonx Orchestrate Export API
================================================================================
ℹ️  Testing export endpoint: http://localhost:7860/api/v1/wxo/32b1f197-4565-4ad9-a214-29bc05ae0270/export
✅ Export API returned 62 tools
ℹ️  Toolkit name: starter_project
ℹ️  MCP URL: http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable

================================================================================
📊 TEST SUMMARY
================================================================================
Total Tests: 5
✅ Passed: 5
✅ Pass Rate: 100.0%
```

### Failed Test Example

```
================================================================================
TEST 1: Health Check
================================================================================
❌ Cannot connect to Langflow: Connection refused

================================================================================
📊 TEST SUMMARY
================================================================================
Total Tests: 1
✅ Passed: 0
❌ Failed: 1
❌ Pass Rate: 0.0%

================================================================================
❌ FAILED TESTS
================================================================================
❌   • Health Check
    Details: Connection refused
```

## Understanding the Tests

### Test 1: Health Check

**Purpose**: Verify Langflow server is running

**Endpoint**: `GET /health`

**Success Criteria**: HTTP 200 response

**Common Failures**:

- Server not running → Start Langflow with `make run_cli`
- Wrong URL → Check `--url` parameter
- Port conflict → Check if port 7860 is available

### Test 2: MCP Streamable Health

**Purpose**: Verify MCP endpoint is accessible

**Endpoint**: `HEAD /api/v1/mcp/streamable` or `HEAD /api/v1/mcp/project/{id}/streamable`

**Success Criteria**: HTTP 200 response

**Common Failures**:

- MCP not initialized → Wait for Langflow to fully start
- Invalid project ID → Check project exists in Langflow

### Test 3: List Tools

**Purpose**: Discover all available MCP tools

**Protocol**: MCP JSON-RPC over HTTP

**Steps**:

1. Send `initialize` request
2. Send `tools/list` request
3. Parse tool list

**Success Criteria**: Returns list of tools with names and descriptions

**Common Failures**:

- No tools found → Check if flows are MCP-enabled
- Invalid response → Check Langflow version supports MCP

### Test 4: Call Tool

**Purpose**: Execute a specific tool with test input

**Protocol**: MCP JSON-RPC over HTTP

**Steps**:

1. Initialize connection
2. Send `tools/call` request with tool name and arguments
3. Parse result

**Success Criteria**: Tool executes and returns result

**Common Failures**:

- Tool not found → Check tool name spelling
- Invalid arguments → Check tool's input schema
- Execution error → Check tool configuration (API keys, etc.)

### Test 5: Export API

**Purpose**: Validate watsonx Orchestrate export functionality

**Endpoint**: `GET /api/v1/wxo/{project_id}/export`

**Success Criteria**: Returns toolkit config, agent YAML, and import commands

**Common Failures**:

- No project ID → Provide `--project-id` parameter
- Invalid project → Check project exists
- Missing tools → Ensure flows are MCP-enabled

## Advanced Usage

### Testing Multiple Projects

```bash
# Create a test script
cat > test_all_projects.sh << 'EOF'
#!/bin/bash

PROJECT_IDS=(
  "32b1f197-4565-4ad9-a214-29bc05ae0270"
  "another-project-id-here"
  "yet-another-project-id"
)

for project_id in "${PROJECT_IDS[@]}"; do
  echo "Testing project: $project_id"
  uv run python scripts/test_mcp_client.py --project-id "$project_id"
  echo ""
done
EOF

chmod +x test_all_projects.sh
./test_all_projects.sh
```

### Continuous Integration

```yaml
# .github/workflows/mcp-tests.yml
name: MCP Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          make init
          uv pip install mcp httpx

      - name: Start Langflow
        run: |
          make run_cli &
          sleep 10  # Wait for server to start

      - name: Run MCP tests
        run: |
          uv run python scripts/test_mcp_client.py --verbose
```

### Custom Test Scenarios

```python
# custom_mcp_test.py
import asyncio
from scripts.test_mcp_client import MCPClientTester

async def custom_test():
    tester = MCPClientTester(
        base_url="http://localhost:7860",
        project_id="your-project-id",
        verbose=True
    )

    try:
        # Run health checks
        await tester.test_health_check()
        await tester.test_mcp_streamable_health()

        # List tools
        tools = await tester.test_list_tools_http()

        # Test specific tools with custom arguments
        await tester.test_call_tool_http(
            "basic_prompting",
            {"input_value": "Explain quantum computing in simple terms"}
        )

        await tester.test_call_tool_http(
            "document_qa",
            {
                "input_value": "What are the key findings?",
                "file_path": "/path/to/document.pdf"
            }
        )

        # Test export
        await tester.test_export_api()

        # Print results
        tester.print_summary()

    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(custom_test())
```

## Troubleshooting

### Connection Refused

**Problem**: Cannot connect to Langflow

**Solutions**:

1. Check if Langflow is running: `curl http://localhost:7860/health`
2. Verify port: `lsof -i :7860`
3. Check firewall settings
4. Try different URL: `--url http://127.0.0.1:7860`

### No Tools Found

**Problem**: MCP endpoint returns empty tool list

**Solutions**:

1. Check if flows are MCP-enabled in Langflow UI
2. Verify project has flows: Open project in Langflow
3. Check MCP settings: Flow Settings → Enable MCP
4. Restart Langflow: `make run_clic`

### Tool Execution Fails

**Problem**: Tool call returns error

**Solutions**:

1. Check tool configuration in Langflow
2. Verify API keys are set (OpenAI, etc.)
3. Check input arguments match tool schema
4. Enable verbose mode: `--verbose`
5. Check Langflow logs for errors

### Export API Fails

**Problem**: Export endpoint returns error

**Solutions**:

1. Verify project ID is correct
2. Check project exists in Langflow
3. Ensure project has MCP-enabled flows
4. Check Langflow version supports export API

### Authentication Errors

**Problem**: 401 Unauthorized responses

**Solutions**:

1. Check if Langflow requires authentication
2. Add API key to request headers (modify script)
3. Verify user permissions
4. Check project access rights

## MCP Protocol Details

### JSON-RPC Format

All MCP requests use JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method_name",
  "params": {
    "param1": "value1"
  }
}
```

### Initialize Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "test-client",
      "version": "1.0.0"
    }
  }
}
```

### List Tools Request

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Call Tool Request

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "basic_prompting",
    "arguments": {
      "input_value": "Write a haiku"
    }
  }
}
```

## Performance Benchmarking

### Measure Tool Execution Time

```python
import time
import asyncio
from scripts.test_mcp_client import MCPClientTester

async def benchmark_tool(tool_name: str, iterations: int = 10):
    tester = MCPClientTester()

    times = []
    for i in range(iterations):
        start = time.time()
        await tester.test_call_tool_http(tool_name, {"input_value": "test"})
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"Iteration {i+1}: {elapsed:.2f}s")

    avg_time = sum(times) / len(times)
    print(f"\nAverage execution time: {avg_time:.2f}s")

    await tester.cleanup()

asyncio.run(benchmark_tool("basic_prompting", iterations=5))
```

## Integration with watsonx Orchestrate

After successful MCP tests, you can:

1. **Export Configuration**:

   ```bash
   uv run python scripts/test_mcp_client.py --project-id YOUR_ID
   # Verify export API test passes
   ```

2. **Deploy to Public URL**:

   ```bash
   ngrok http 7860
   # Test with public URL
   uv run python scripts/test_mcp_client.py --url https://abc123.ngrok.io
   ```

3. **Import to watsonx**:

   ```bash
   cd wxo_export
   ./import_toolkit.sh
   ```

4. **Test in watsonx**:
   ```bash
   orchestrate agents run starter_project_agent --prompt "Hello!"
   ```

## Best Practices

1. **Always test locally first** before deploying to production
2. **Use verbose mode** when debugging issues
3. **Test specific tools** that are critical for your use case
4. **Automate tests** in CI/CD pipeline
5. **Monitor performance** with benchmarking
6. **Keep test data** separate from production data
7. **Document custom tests** for your team

## Next Steps

- ✅ Test MCP server locally
- ✅ Verify all tools work correctly
- ✅ Test export API
- 🔄 Deploy to public URL (ngrok or IBM Cloud)
- 🔄 Import to watsonx Orchestrate
- 🔄 Test end-to-end integration

## Support

- **Documentation**: See other guides in `docs/` directory
- **Issues**: Check Langflow GitHub issues
- **Community**: Langflow Discord/Discussions

---

**Last Updated**: March 18, 2026  
**Script Version**: 1.0.0  
**Langflow Version**: 1.0+
