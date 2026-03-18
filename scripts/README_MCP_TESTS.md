# MCP Client Tests - Quick Reference

## Quick Start

```bash
# 1. Install dependencies
uv pip install mcp httpx

# 2. Start Langflow
make run_cli

# 3. Run tests (in another terminal)
uv run python scripts/test_mcp_client.py
```

## Common Commands

### Basic Tests

```bash
# Test default (localhost:7860)
uv run python scripts/test_mcp_client.py

# Test with verbose output
uv run python scripts/test_mcp_client.py --verbose

# Test specific project
uv run python scripts/test_mcp_client.py --project-id 32b1f197-4565-4ad9-a214-29bc05ae0270
```

### Tool Testing

```bash
# Test specific tools
uv run python scripts/test_mcp_client.py --tools basic_prompting,document_qa

# Test with project and tools
uv run python scripts/test_mcp_client.py \
  --project-id 32b1f197-4565-4ad9-a214-29bc05ae0270 \
  --tools basic_prompting,simple_agent \
  --verbose
```

### Remote Testing

```bash
# Test ngrok deployment
uv run python scripts/test_mcp_client.py --url https://abc123.ngrok.io

# Test IBM Cloud deployment
uv run python scripts/test_mcp_client.py --url https://your-app.cloud.ibm.com
```

## What Gets Tested

1. ✅ **Health Check** - Langflow server is running
2. ✅ **MCP Endpoint** - MCP Streamable HTTP is accessible
3. ✅ **Tool Discovery** - List all available tools
4. ✅ **Tool Execution** - Call tools with test inputs (optional)
5. ✅ **Export API** - watsonx Orchestrate export (if project ID provided)

## Expected Output

```
================================================================================
🚀 LANGFLOW MCP CLIENT TEST SUITE
================================================================================
ℹ️  Base URL: http://localhost:7860

✅ Langflow server is running
✅ MCP Streamable HTTP endpoint is healthy
✅ Found 62 tools
✅ Export API returned 62 tools

================================================================================
📊 TEST SUMMARY
================================================================================
Total Tests: 4
✅ Passed: 4
✅ Pass Rate: 100.0%
```

## Troubleshooting

### "Cannot connect to Langflow"

```bash
# Check if Langflow is running
curl http://localhost:7860/health

# Start Langflow
make run_cli
```

### "No tools found"

```bash
# Check if flows are MCP-enabled
# Open Langflow UI → Flow Settings → Enable MCP

# Restart Langflow
make run_clic
```

### "Tool execution failed"

```bash
# Check API keys are configured
# Open Langflow UI → Settings → API Keys

# Run with verbose mode to see details
uv run python scripts/test_mcp_client.py --verbose
```

## Full Documentation

See `docs/MCP_CLIENT_TESTING_GUIDE.md` for complete documentation.

## Integration Testing Flow

```bash
# 1. Test locally
uv run python scripts/test_mcp_client.py --project-id YOUR_PROJECT_ID

# 2. Deploy with ngrok
ngrok http 7860

# 3. Test public URL
uv run python scripts/test_mcp_client.py --url https://abc123.ngrok.io

# 4. Export for watsonx
# Files are in wxo_export/ directory

# 5. Import to watsonx Orchestrate
cd wxo_export
./import_toolkit.sh
```

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

Use in CI/CD:

```bash
if uv run python scripts/test_mcp_client.py; then
  echo "Tests passed!"
else
  echo "Tests failed!"
  exit 1
fi
```

## Help

```bash
# Show all options
uv run python scripts/test_mcp_client.py --help
```

---

**Quick Links**:

- Full Guide: `docs/MCP_CLIENT_TESTING_GUIDE.md`
- Integration README: `WATSONX_INTEGRATION_README.md`
- Main Documentation: `README_WATSONX_INTEGRATION.md`
