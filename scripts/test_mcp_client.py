#!/usr/bin/env python3
"""
MCP Client Test Script

This script programmatically tests the Langflow MCP server by:
1. Connecting to the MCP server (both SSE and Streamable HTTP transports)
2. Listing available tools
3. Calling specific tools with test inputs
4. Validating responses

Usage:
    # Test with default settings (localhost:7860)
    uv run python scripts/test_mcp_client.py

    # Test with custom URL
    uv run python scripts/test_mcp_client.py --url http://localhost:7860

    # Test specific project
    uv run python scripts/test_mcp_client.py --project-id 32b1f197-4565-4ad9-a214-29bc05ae0270

    # Test specific tools only
    uv run python scripts/test_mcp_client.py --tools basic_prompting,document_qa

    # Verbose output
    uv run python scripts/test_mcp_client.py --verbose
"""

import argparse
import asyncio
import json
import sys
from typing import Any
from uuid import UUID

try:
    import httpx
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: uv pip install mcp httpx")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class MCPClientTester:
    """Test client for Langflow MCP server."""

    def __init__(
        self,
        base_url: str = "http://localhost:7860",
        project_id: str | None = None,
        verbose: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.verbose = verbose
        # MCP Streamable HTTP requires specific Accept headers
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)
        self.test_results: dict[str, Any] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "tests": [],
        }

    def log(self, message: str, color: str = "") -> None:
        """Log a message with optional color."""
        if color:
            print(f"{color}{message}{Colors.ENDC}")
        else:
            print(message)

    def log_verbose(self, message: str) -> None:
        """Log verbose message."""
        if self.verbose:
            print(f"{Colors.OKCYAN}[VERBOSE] {message}{Colors.ENDC}")

    def log_success(self, message: str) -> None:
        """Log success message."""
        self.log(f"✅ {message}", Colors.OKGREEN)

    def log_error(self, message: str) -> None:
        """Log error message."""
        self.log(f"❌ {message}", Colors.FAIL)

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.log(f"⚠️  {message}", Colors.WARNING)

    def log_info(self, message: str) -> None:
        """Log info message."""
        self.log(f"ℹ️  {message}", Colors.OKBLUE)

    def record_test(self, name: str, passed: bool, details: str = "") -> None:
        """Record test result."""
        self.test_results["total"] += 1
        if passed:
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1

        self.test_results["tests"].append(
            {"name": name, "passed": passed, "details": details}
        )

    async def test_health_check(self) -> bool:
        """Test if Langflow server is running."""
        self.log("\n" + "=" * 80, Colors.HEADER)
        self.log("TEST 1: Health Check", Colors.HEADER)
        self.log("=" * 80, Colors.HEADER)

        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.log_success("Langflow server is running")
                self.log_verbose(f"Response: {response.json()}")
                self.record_test("Health Check", True)
                return True
            else:
                self.log_error(
                    f"Health check failed with status {response.status_code}"
                )
                self.record_test("Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_error(f"Cannot connect to Langflow: {e}")
            self.record_test("Health Check", False, str(e))
            return False

    async def test_mcp_streamable_health(self) -> bool:
        """Test MCP Streamable HTTP health endpoint."""
        self.log("\n" + "=" * 80, Colors.HEADER)
        self.log("TEST 2: MCP Streamable HTTP Health Check", Colors.HEADER)
        self.log("=" * 80, Colors.HEADER)

        endpoint = f"{self.base_url}/api/v1/mcp/streamable"
        if self.project_id:
            endpoint = f"{self.base_url}/api/v1/mcp/project/{self.project_id}/streamable"

        try:
            # HEAD request for health check
            response = await self.client.head(endpoint)
            if response.status_code == 200:
                self.log_success("MCP Streamable HTTP endpoint is healthy")
                self.log_info(f"Endpoint: {endpoint}")
                self.record_test("MCP Streamable Health", True)
                return True
            else:
                self.log_error(
                    f"MCP health check failed with status {response.status_code}"
                )
                self.record_test(
                    "MCP Streamable Health", False, f"Status: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_error(f"MCP health check failed: {e}")
            self.record_test("MCP Streamable Health", False, str(e))
            return False

    async def test_list_tools_http(self) -> list[dict] | None:
        """Test listing tools via HTTP API."""
        self.log("\n" + "=" * 80, Colors.HEADER)
        self.log("TEST 3: List Tools (HTTP API)", Colors.HEADER)
        self.log("=" * 80, Colors.HEADER)

        endpoint = f"{self.base_url}/api/v1/mcp/streamable"
        if self.project_id:
            endpoint = f"{self.base_url}/api/v1/mcp/project/{self.project_id}/streamable"

        try:
            # MCP protocol: initialize connection
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }

            self.log_verbose(f"Sending initialize request to {endpoint}")
            response = await self.client.post(endpoint, json=init_payload)

            if response.status_code != 200:
                self.log_error(f"Initialize failed with status {response.status_code}")
                self.log_verbose(f"Response: {response.text}")
                self.record_test("List Tools (HTTP)", False, f"Status: {response.status_code}")
                return None

            init_result = response.json()
            self.log_verbose(f"Initialize response: {json.dumps(init_result, indent=2)}")

            # List tools
            list_tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }

            self.log_verbose("Sending tools/list request")
            response = await self.client.post(endpoint, json=list_tools_payload)

            if response.status_code != 200:
                self.log_error(f"List tools failed with status {response.status_code}")
                self.log_verbose(f"Response: {response.text}")
                self.record_test("List Tools (HTTP)", False, f"Status: {response.status_code}")
                return None

            result = response.json()
            self.log_verbose(f"List tools response: {json.dumps(result, indent=2)}")

            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                self.log_success(f"Found {len(tools)} tools")

                # Display first 5 tools
                for i, tool in enumerate(tools[:5], 1):
                    self.log_info(f"  {i}. {tool['name']}: {tool.get('description', 'No description')[:80]}")

                if len(tools) > 5:
                    self.log_info(f"  ... and {len(tools) - 5} more tools")

                self.record_test("List Tools (HTTP)", True, f"Found {len(tools)} tools")
                return tools
            else:
                self.log_error("Invalid response format")
                self.log_verbose(f"Response: {json.dumps(result, indent=2)}")
                self.record_test("List Tools (HTTP)", False, "Invalid response format")
                return None

        except Exception as e:
            self.log_error(f"List tools failed: {e}")
            self.record_test("List Tools (HTTP)", False, str(e))
            return None

    async def test_call_tool_http(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> bool:
        """Test calling a specific tool via HTTP API."""
        self.log("\n" + "=" * 80, Colors.HEADER)
        self.log(f"TEST: Call Tool '{tool_name}'", Colors.HEADER)
        self.log("=" * 80, Colors.HEADER)

        endpoint = f"{self.base_url}/api/v1/mcp/streamable"
        if self.project_id:
            endpoint = f"{self.base_url}/api/v1/mcp/project/{self.project_id}/streamable"

        try:
            # Initialize connection first
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }

            await self.client.post(endpoint, json=init_payload)

            # Call tool
            call_tool_payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }

            self.log_info(f"Calling tool: {tool_name}")
            self.log_verbose(f"Arguments: {json.dumps(arguments, indent=2)}")

            response = await self.client.post(endpoint, json=call_tool_payload)

            if response.status_code != 200:
                self.log_error(f"Tool call failed with status {response.status_code}")
                self.log_verbose(f"Response: {response.text}")
                self.record_test(f"Call Tool: {tool_name}", False, f"Status: {response.status_code}")
                return False

            result = response.json()
            self.log_verbose(f"Tool call response: {json.dumps(result, indent=2)}")

            if "result" in result:
                self.log_success(f"Tool '{tool_name}' executed successfully")

                # Display result content
                if "content" in result["result"]:
                    content = result["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        first_content = content[0]
                        if "text" in first_content:
                            text = first_content["text"]
                            # Truncate long responses
                            if len(text) > 200:
                                self.log_info(f"Result: {text[:200]}...")
                            else:
                                self.log_info(f"Result: {text}")

                self.record_test(f"Call Tool: {tool_name}", True)
                return True
            elif "error" in result:
                error = result["error"]
                self.log_error(f"Tool execution error: {error.get('message', 'Unknown error')}")
                self.log_verbose(f"Error details: {json.dumps(error, indent=2)}")
                self.record_test(f"Call Tool: {tool_name}", False, error.get("message", "Unknown error"))
                return False
            else:
                self.log_error("Invalid response format")
                self.log_verbose(f"Response: {json.dumps(result, indent=2)}")
                self.record_test(f"Call Tool: {tool_name}", False, "Invalid response format")
                return False

        except Exception as e:
            self.log_error(f"Tool call failed: {e}")
            self.record_test(f"Call Tool: {tool_name}", False, str(e))
            return False

    async def test_export_api(self) -> bool:
        """Test the watsonx Orchestrate export API."""
        self.log("\n" + "=" * 80, Colors.HEADER)
        self.log("TEST: watsonx Orchestrate Export API", Colors.HEADER)
        self.log("=" * 80, Colors.HEADER)

        if not self.project_id:
            self.log_warning("Skipping export API test (no project ID provided)")
            return True

        endpoint = f"{self.base_url}/api/v1/wxo/{self.project_id}/export"

        try:
            self.log_info(f"Testing export endpoint: {endpoint}")
            response = await self.client.get(endpoint)

            if response.status_code != 200:
                self.log_error(f"Export API failed with status {response.status_code}")
                self.log_verbose(f"Response: {response.text}")
                self.record_test("Export API", False, f"Status: {response.status_code}")
                return False

            result = response.json()
            self.log_verbose(f"Export response keys: {list(result.keys())}")

            # Validate response structure
            required_keys = ["toolkit_config", "agent_yaml", "cli_import_command"]
            missing_keys = [key for key in required_keys if key not in result]

            if missing_keys:
                self.log_error(f"Missing required keys: {missing_keys}")
                self.record_test("Export API", False, f"Missing keys: {missing_keys}")
                return False

            # Validate toolkit_config
            toolkit_config = result["toolkit_config"]
            if "tools" in toolkit_config:
                tool_count = len(toolkit_config["tools"])
                self.log_success(f"Export API returned {tool_count} tools")
                self.log_info(f"Toolkit name: {toolkit_config.get('toolkit_name', 'N/A')}")
                self.log_info(f"MCP URL: {toolkit_config.get('mcp_url', 'N/A')}")
                self.record_test("Export API", True, f"{tool_count} tools exported")
                return True
            else:
                self.log_error("Invalid toolkit_config structure")
                self.record_test("Export API", False, "Invalid toolkit_config")
                return False

        except Exception as e:
            self.log_error(f"Export API test failed: {e}")
            self.record_test("Export API", False, str(e))
            return False

    async def run_all_tests(self, test_tools: list[str] | None = None) -> None:
        """Run all tests."""
        self.log("\n" + "=" * 80, Colors.BOLD)
        self.log("🚀 LANGFLOW MCP CLIENT TEST SUITE", Colors.BOLD)
        self.log("=" * 80, Colors.BOLD)
        self.log_info(f"Base URL: {self.base_url}")
        if self.project_id:
            self.log_info(f"Project ID: {self.project_id}")
        self.log("")

        # Test 1: Health check
        if not await self.test_health_check():
            self.log_error("Langflow server is not running. Aborting tests.")
            return

        # Test 2: MCP health check
        await self.test_mcp_streamable_health()

        # Test 3: List tools
        tools = await self.test_list_tools_http()

        # Test 4: Call specific tools
        if tools and test_tools:
            for tool_name in test_tools:
                # Find tool in list
                tool = next((t for t in tools if t["name"] == tool_name), None)
                if tool:
                    # Prepare test arguments based on tool schema
                    arguments = self._prepare_test_arguments(tool)
                    await self.test_call_tool_http(tool_name, arguments)
                else:
                    self.log_warning(f"Tool '{tool_name}' not found in available tools")

        # Test 5: Export API
        await self.test_export_api()

        # Print summary
        self.print_summary()

    def _prepare_test_arguments(self, tool: dict) -> dict[str, Any]:
        """Prepare test arguments for a tool based on its schema."""
        # Default test arguments for common tools
        default_args = {
            "basic_prompting": {"input_value": "Write a haiku about AI"},
            "document_qa": {
                "input_value": "What is this document about?",
                "file_path": "test.pdf",
            },
            "simple_agent": {"input_value": "Hello, how are you?"},
        }

        tool_name = tool["name"]

        # Return default args if available
        if tool_name in default_args:
            return default_args[tool_name]

        # Otherwise, try to infer from schema
        if "inputSchema" in tool:
            schema = tool["inputSchema"]
            if "properties" in schema:
                # Create minimal valid arguments
                args = {}
                for prop_name, prop_schema in schema["properties"].items():
                    if prop_schema.get("type") == "string":
                        args[prop_name] = "test input"
                return args

        # Fallback: generic input
        return {"input_value": "test"}

    def print_summary(self) -> None:
        """Print test summary."""
        self.log("\n" + "=" * 80, Colors.BOLD)
        self.log("📊 TEST SUMMARY", Colors.BOLD)
        self.log("=" * 80, Colors.BOLD)

        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]

        self.log(f"Total Tests: {total}")
        self.log_success(f"Passed: {passed}")
        if failed > 0:
            self.log_error(f"Failed: {failed}")

        # Calculate pass rate
        if total > 0:
            pass_rate = (passed / total) * 100
            if pass_rate == 100:
                self.log_success(f"Pass Rate: {pass_rate:.1f}%")
            elif pass_rate >= 80:
                self.log_warning(f"Pass Rate: {pass_rate:.1f}%")
            else:
                self.log_error(f"Pass Rate: {pass_rate:.1f}%")

        # Print failed tests
        if failed > 0:
            self.log("\n" + "=" * 80, Colors.FAIL)
            self.log("❌ FAILED TESTS", Colors.FAIL)
            self.log("=" * 80, Colors.FAIL)
            for test in self.test_results["tests"]:
                if not test["passed"]:
                    self.log_error(f"  • {test['name']}")
                    if test["details"]:
                        self.log(f"    Details: {test['details']}")

        self.log("")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.client.aclose()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Langflow MCP server programmatically"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:7860",
        help="Langflow base URL (default: http://localhost:7860)",
    )
    parser.add_argument(
        "--project-id",
        help="Project ID to test (optional, tests project-specific endpoints)",
    )
    parser.add_argument(
        "--tools",
        help="Comma-separated list of tools to test (e.g., basic_prompting,document_qa)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Parse tools list
    test_tools = None
    if args.tools:
        test_tools = [t.strip() for t in args.tools.split(",")]

    # Create tester
    tester = MCPClientTester(
        base_url=args.url, project_id=args.project_id, verbose=args.verbose
    )

    try:
        await tester.run_all_tests(test_tools=test_tools)
    finally:
        await tester.cleanup()

    # Exit with appropriate code
    if tester.test_results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
