# watsonx Orchestrate Integration - Complete Setup Guide

## Your Langflow MCP Server Details

**Project**: lf-starter_project  
**Project ID**: 32b1f197-4565-4ad9-a214-29bc05ae0270  
**MCP Endpoint**: http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable

---

## Option 1: Quick Setup (CLI Method)

### Step 1: Import Langflow Tools to watsonx Orchestrate

```bash
orchestrate toolkits add \
  --name langflow-starter \
  --type mcp \
  --url http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
```

### Step 2: Verify Import

```bash
orchestrate toolkits list
```

You should see `langflow-starter` with 62 tools listed.

### Step 3: Create an Agent

Create a file `customer_support_agent.yaml`:

```yaml
name: customer_support_agent
description: Helpful assistant with web search and calculator capabilities
llm:
  provider: groq
  model: openai/gpt-oss-120b
tools:
  - langflow-starter.simple_agent
```

### Step 4: Import the Agent

```bash
orchestrate agents import customer_support_agent.yaml
```

### Step 5: Test the Agent

```bash
orchestrate agents test customer_support_agent \
  --input "What is 25 multiplied by 48?"
```

---

## Option 2: Configuration File Method

### Step 1: Create MCP Configuration

Create or edit your watsonx Orchestrate MCP configuration file:

**For Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**For Cursor**: `~/.cursor/mcp.json`  
**For Windsurf**: `~/.codeium/windsurf/mcp_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "langflow-starter": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "--transport",
        "streamablehttp",
        "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable"
      ],
      "env": {}
    }
  }
}
```

### Step 2: Restart watsonx Orchestrate

Restart the application to load the new MCP server.

### Step 3: Verify Connection

The Langflow tools should now be available in watsonx Orchestrate.

---

## Option 3: With Authentication (Recommended for Production)

### Step 1: Generate API Key in Langflow

1. Go to Langflow Settings → API Keys
2. Click "Create API Key"
3. Name: `watsonx Orchestrate Integration`
4. Copy the generated key (starts with `sk-`)

### Step 2: Add to watsonx Orchestrate with Authentication

```json
{
  "mcpServers": {
    "langflow-starter": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "--transport",
        "streamablehttp",
        "http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable"
      ],
      "env": {
        "LANGFLOW_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

---

## Available Tools from Your Langflow Project

Your `lf-starter_project` exposes **62 tools** via MCP, including:

- **simple_agent** - Your custom agent with URL and Calculator tools
- All other flows in your starter project

### To see all available tools:

```bash
orchestrate toolkits describe langflow-starter
```

Or visit in browser:

```
http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/tools
```

---

## Example Agents

### 1. Simple Assistant Agent

```yaml
name: simple_assistant
description: Basic assistant with calculation and web search
llm:
  provider: groq
  model: openai/gpt-oss-120b
tools:
  - langflow-starter.simple_agent
```

### 2. Multi-Tool Agent

```yaml
name: multi_tool_agent
description: Agent with access to multiple Langflow tools
llm:
  provider: groq
  model: openai/gpt-oss-120b
tools:
  - langflow-starter.simple_agent
  - langflow-starter.vector_store_rag
  - langflow-starter.basic_prompting
```

### 3. Customer Support Agent

```yaml
name: customer_support
description: Handles customer inquiries with knowledge base and tools
llm:
  provider: groq
  model: openai/gpt-oss-120b
tools:
  - langflow-starter.simple_agent
system_prompt: |
  You are a helpful customer support agent. Use the available tools to:
  - Search the knowledge base for answers
  - Perform calculations when needed
  - Fetch information from URLs
  Always be polite and professional.
```

---

## Testing Your Integration

### Test 1: Calculator Tool

```bash
orchestrate agents test customer_support \
  --input "What is 156 divided by 12?"
```

Expected: Agent uses calculator tool and returns 13

### Test 2: Web Search Tool

```bash
orchestrate agents test customer_support \
  --input "Fetch the content from https://example.com"
```

Expected: Agent uses URL tool and returns page content

### Test 3: Combined Tools

```bash
orchestrate agents test customer_support \
  --input "Calculate 25 * 48 and then search for information about that number"
```

Expected: Agent uses both calculator and web search

---

## Troubleshooting

### Issue: "Connection refused"

**Solution**: Make sure Langflow is running:

```bash
cd /Users/kevalshah/Documents/langflow
make run_cli
```

### Issue: "Tools not found"

**Solution**: Verify MCP endpoint is accessible:

```bash
curl http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/tools
```

### Issue: "Authentication failed"

**Solution**:

1. Generate new API key in Langflow
2. Update the `LANGFLOW_API_KEY` in your MCP configuration
3. Restart watsonx Orchestrate

### Issue: "Agent not responding"

**Solution**:

1. Check Langflow logs for errors
2. Verify the flow works in Langflow playground
3. Test MCP endpoint directly with curl

---

## Production Deployment

### For Production Use:

1. **Use HTTPS**: Replace `http://localhost:7860` with your production URL
2. **Add Authentication**: Always use API keys in production
3. **Monitor Performance**: Track response times and errors
4. **Set Rate Limits**: Configure appropriate rate limits
5. **Enable Logging**: Turn on detailed logging for debugging

### Example Production Configuration:

```json
{
  "mcpServers": {
    "langflow-production": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "--transport",
        "streamablehttp",
        "https://langflow.yourcompany.com/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable"
      ],
      "env": {
        "LANGFLOW_API_KEY": "sk-production-key-here"
      }
    }
  }
}
```

---

## Next Steps

1. ✅ **Test the integration** with the examples above
2. ✅ **Create custom agents** for your use cases
3. ✅ **Add more flows** in Langflow (they'll automatically appear in watsonx Orchestrate)
4. ✅ **Monitor usage** and optimize performance
5. ✅ **Deploy to production** when ready

---

## Support

- **Langflow Documentation**: https://docs.langflow.org
- **watsonx Orchestrate Documentation**: https://developer.watson-orchestrate.ibm.com
- **MCP Protocol**: https://modelcontextprotocol.io

---

**Your integration is ready!** 🎉

All 62 tools from your Langflow project are now available in watsonx Orchestrate.
