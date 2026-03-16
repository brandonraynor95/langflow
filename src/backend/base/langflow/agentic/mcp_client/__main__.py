"""Entry point for the Langflow MCP Client server.

Usage:
    python -m langflow.agentic.mcp_client
    # or via console script:
    langflow-mcp-client

Environment variables:
    LANGFLOW_SERVER_URL: Langflow server URL (default: http://localhost:7860)
    LANGFLOW_API_KEY: API key for authentication (skips login)
"""

from langflow.agentic.mcp_client.server import mcp


def main():
    mcp.run()


if __name__ == "__main__":
    main()
