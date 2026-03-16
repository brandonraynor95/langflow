"""Langflow MCP Client — REST API-based MCP server for operating Langflow.

Standalone MCP server that connects to a running Langflow instance via REST API.
Unlike the agentic MCP server (langflow.agentic.mcp), this one requires no
internal Langflow services — just a URL and credentials.

Usage:
    python -m langflow.agentic.mcp_client
    # or via console script:
    langflow-mcp-client
"""
