"""Integration tests for lfx.mcp.server MCP tools.

Uses the client_fixture (real Langflow app via ASGITransport) — no mocking.
Tests the full roundtrip: MCP tool -> LangflowClient -> Langflow API -> DB.
"""

import pytest
from httpx import AsyncClient
from lfx.mcp import server as mcp_server_module
from lfx.mcp.client import LangflowClient


@pytest.fixture
async def mcp_client(client: AsyncClient, logged_in_headers):
    """Wire up a LangflowClient that uses the test's AsyncClient transport."""
    # Extract the token from logged_in_headers
    auth_header = logged_in_headers["Authorization"]
    access_token = auth_header.removeprefix("Bearer ")

    lf_client = LangflowClient(server_url="http://testserver", access_token=access_token)
    # Inject the test's AsyncClient so requests go through ASGITransport
    lf_client._http = client

    # Patch the module-level state in server.py
    old_client = mcp_server_module._client
    old_registry = mcp_server_module._registry
    mcp_server_module._client = lf_client
    mcp_server_module._registry = None

    yield lf_client

    # Restore
    mcp_server_module._client = old_client
    mcp_server_module._registry = old_registry
    # Don't close the injected client — the fixture owns it
    lf_client._http = None


# ---------------------------------------------------------------------------
# Flow tools
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestCreateFlow:
    async def test_create_flow(self):
        result = await mcp_server_module.create_flow("Test Flow", "A test")
        assert "id" in result
        assert result["name"] == "Test Flow"

    async def test_create_flow_default_name(self):
        result = await mcp_server_module.create_flow()
        assert result["name"] == "Untitled Flow"


@pytest.mark.usefixtures("mcp_client")
class TestListFlows:
    async def test_list_flows_empty(self):
        flows = await mcp_server_module.list_flows()
        # May contain example flows, but should be a list
        assert isinstance(flows, list)

    async def test_list_flows_after_create(self):
        await mcp_server_module.create_flow("ListTest")
        flows = await mcp_server_module.list_flows()
        names = [f["name"] for f in flows]
        assert "ListTest" in names


@pytest.mark.usefixtures("mcp_client")
class TestGetFlowInfo:
    async def test_get_flow_info(self):
        created = await mcp_server_module.create_flow("InfoTest", "desc")
        info = await mcp_server_module.get_flow_info(created["id"])
        assert info["id"] == created["id"]
        assert info["name"] == "InfoTest"
        assert info["node_count"] == 0
        assert info["edge_count"] == 0


@pytest.mark.usefixtures("mcp_client")
class TestDeleteFlow:
    async def test_delete_flow(self):
        created = await mcp_server_module.create_flow("DeleteMe")
        result = await mcp_server_module.delete_flow(created["id"])
        assert result["deleted"] == created["id"]

        # Verify it's gone
        with pytest.raises(RuntimeError, match="failed"):
            await mcp_server_module.get_flow_info(created["id"])


# ---------------------------------------------------------------------------
# Component tools
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestAddComponent:
    async def test_add_component(self):
        created = await mcp_server_module.create_flow("CompTest")
        result = await mcp_server_module.add_component(created["id"], "ChatInput")
        assert result["id"].startswith("ChatInput-")
        assert result["display_name"] == "Chat Input"

    async def test_add_unknown_component_raises(self):
        created = await mcp_server_module.create_flow("CompTest2")
        with pytest.raises(ValueError, match="Unknown component"):
            await mcp_server_module.add_component(created["id"], "TotallyFake")


@pytest.mark.usefixtures("mcp_client")
class TestRemoveComponent:
    async def test_remove_component(self):
        created = await mcp_server_module.create_flow("RemoveTest")
        comp = await mcp_server_module.add_component(created["id"], "ChatInput")
        result = await mcp_server_module.remove_component(created["id"], comp["id"])
        assert result["removed"] == comp["id"]

        # Verify it's gone
        components = await mcp_server_module.list_components(created["id"])
        assert len(components) == 0


@pytest.mark.usefixtures("mcp_client")
class TestListComponents:
    async def test_list_components(self):
        created = await mcp_server_module.create_flow("ListCompTest")
        await mcp_server_module.add_component(created["id"], "ChatInput")
        await mcp_server_module.add_component(created["id"], "ChatOutput")
        components = await mcp_server_module.list_components(created["id"])
        types = {c["type"] for c in components}
        assert "ChatInput" in types
        assert "ChatOutput" in types


@pytest.mark.usefixtures("mcp_client")
class TestGetComponentInfo:
    async def test_get_component_info(self):
        created = await mcp_server_module.create_flow("GetCompTest")
        comp = await mcp_server_module.add_component(created["id"], "ChatInput")
        info = await mcp_server_module.get_component_info(created["id"], comp["id"])
        assert info["id"] == comp["id"]
        assert info["type"] == "ChatInput"
        assert "params" in info

    async def test_get_component_info_redacts_secrets(self):
        created = await mcp_server_module.create_flow("RedactTest")
        comp = await mcp_server_module.add_component(created["id"], "OpenAIModel")
        # Configure an API key
        await mcp_server_module.configure_component(
            created["id"],
            comp["id"],
            {"api_key": "sk-test-fake-12345"},  # pragma: allowlist secret
        )
        info = await mcp_server_module.get_component_info(created["id"], comp["id"])
        assert info["params"]["api_key"] == "***REDACTED***"

    async def test_get_single_field(self):
        created = await mcp_server_module.create_flow("FieldTest")
        comp = await mcp_server_module.add_component(created["id"], "ChatInput")
        await mcp_server_module.configure_component(created["id"], comp["id"], {"input_value": "Hello world"})
        result = await mcp_server_module.get_component_info(created["id"], comp["id"], field_name="input_value")
        assert result["component_id"] == comp["id"]
        assert result["field_name"] == "input_value"
        assert result["value"] == "Hello world"
        assert "display_name" in result
        assert "type" in result

    async def test_get_single_field_unknown_raises(self):
        created = await mcp_server_module.create_flow("FieldTest2")
        comp = await mcp_server_module.add_component(created["id"], "ChatInput")
        with pytest.raises(ValueError, match="Field 'nonexistent' not found"):
            await mcp_server_module.get_component_info(created["id"], comp["id"], field_name="nonexistent")

    async def test_get_single_field_redacts_secret(self):
        created = await mcp_server_module.create_flow("FieldRedact")
        comp = await mcp_server_module.add_component(created["id"], "OpenAIModel")
        await mcp_server_module.configure_component(
            created["id"],
            comp["id"],
            {"api_key": "sk-test-fake"},  # pragma: allowlist secret
        )
        result = await mcp_server_module.get_component_info(created["id"], comp["id"], field_name="api_key")
        assert result["value"] == "***REDACTED***"


# ---------------------------------------------------------------------------
# Configure component
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestConfigureComponent:
    async def test_configure_static_param(self):
        created = await mcp_server_module.create_flow("ConfigTest")
        comp = await mcp_server_module.add_component(created["id"], "ChatInput")
        result = await mcp_server_module.configure_component(created["id"], comp["id"], {"input_value": "Hello"})
        assert result["component_id"] == comp["id"]
        assert "input_value" in result["configured"]

        # Verify the value was set
        info = await mcp_server_module.get_component_info(created["id"], comp["id"])
        assert info["params"]["input_value"] == "Hello"

    async def test_configure_nonexistent_component_raises(self):
        created = await mcp_server_module.create_flow("ConfigTest2")
        with pytest.raises(ValueError, match="Component not found"):
            await mcp_server_module.configure_component(created["id"], "NoSuch-12345", {"key": "val"})

    async def test_configure_dynamic_field(self):
        """Fields with real_time_refresh trigger /custom_component/update."""
        created = await mcp_server_module.create_flow("DynamicTest")
        comp = await mcp_server_module.add_component(created["id"], "OpenAIModel")
        # model_name has real_time_refresh=True
        result = await mcp_server_module.configure_component(created["id"], comp["id"], {"model_name": "gpt-4o"})
        assert "model_name" in result["configured"]


# ---------------------------------------------------------------------------
# Connection tools
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestConnectComponents:
    async def test_connect_components(self):
        created = await mcp_server_module.create_flow("ConnectTest")
        c1 = await mcp_server_module.add_component(created["id"], "ChatInput")
        c2 = await mcp_server_module.add_component(created["id"], "ChatOutput")
        result = await mcp_server_module.connect_components(created["id"], c1["id"], "message", c2["id"], "input_value")
        assert result["source_id"] == c1["id"]
        assert result["target_id"] == c2["id"]

        # Verify via flow info
        info = await mcp_server_module.get_flow_info(created["id"])
        assert info["edge_count"] == 1

    async def test_connect_component_as_tool_auto_enables_tool_mode(self):
        created = await mcp_server_module.create_flow("ToolModeAutoTest")
        url_comp = await mcp_server_module.add_component(created["id"], "URLComponent")
        agent = await mcp_server_module.add_component(created["id"], "Agent")

        # Before: normal outputs
        info = await mcp_server_module.get_component_info(created["id"], url_comp["id"])
        output_names = [o["name"] for o in info["outputs"]]
        assert "component_as_tool" not in output_names

        # Connect via component_as_tool — should auto-enable tool_mode
        await mcp_server_module.connect_components(
            created["id"], url_comp["id"], "component_as_tool", agent["id"], "tools"
        )

        # After: tool_mode enabled, output switched
        info = await mcp_server_module.get_component_info(created["id"], url_comp["id"])
        output_names = [o["name"] for o in info["outputs"]]
        assert output_names == ["component_as_tool"]


@pytest.mark.usefixtures("mcp_client")
class TestDisconnectComponents:
    async def test_disconnect_components(self):
        created = await mcp_server_module.create_flow("DisconnectTest")
        c1 = await mcp_server_module.add_component(created["id"], "ChatInput")
        c2 = await mcp_server_module.add_component(created["id"], "ChatOutput")
        await mcp_server_module.connect_components(created["id"], c1["id"], "message", c2["id"], "input_value")
        result = await mcp_server_module.disconnect_components(created["id"], c1["id"], c2["id"])
        assert result["removed_count"] == 1

        # Verify
        info = await mcp_server_module.get_flow_info(created["id"])
        assert info["edge_count"] == 0

    async def test_disconnect_no_match_raises(self):
        created = await mcp_server_module.create_flow("DisconnectNoMatch")
        c1 = await mcp_server_module.add_component(created["id"], "ChatInput")
        c2 = await mcp_server_module.add_component(created["id"], "ChatOutput")
        # No connection exists between them
        with pytest.raises(ValueError, match="No connections found"):
            await mcp_server_module.disconnect_components(created["id"], c1["id"], c2["id"])


# ---------------------------------------------------------------------------
# Search / Describe (registry)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestSearchComponentTypes:
    async def test_search_all(self):
        results = await mcp_server_module.search_component_types()
        assert len(results) > 0

    async def test_search_by_query(self):
        results = await mcp_server_module.search_component_types(query="Chat")
        types = {r["type"] for r in results}
        assert "ChatInput" in types

    async def test_search_by_category(self):
        results = await mcp_server_module.search_component_types(category="inputs")
        assert all(r["category"] == "inputs" for r in results)

    async def test_search_by_output_type(self):
        results = await mcp_server_module.search_component_types(output_type="LanguageModel")
        assert len(results) > 0
        types = {r["type"] for r in results}
        assert "OpenAIModel" in types


@pytest.mark.usefixtures("mcp_client")
class TestDescribeComponentType:
    async def test_describe_chat_input(self):
        info = await mcp_server_module.describe_component_type("ChatInput")
        assert info["type"] == "ChatInput"
        assert "inputs" in info
        assert "outputs" in info

    async def test_describe_advanced_fields(self):
        info = await mcp_server_module.describe_component_type("OpenAIModel")
        assert "advanced_fields" in info
        assert isinstance(info["advanced_fields"], list)
        # Advanced fields should not appear in inputs or fields
        advanced = set(info["advanced_fields"])
        input_names = {i["name"] for i in info.get("inputs", [])}
        field_names = {f["name"] for f in info.get("fields", [])}
        assert not advanced & input_names
        assert not advanced & field_names

    async def test_describe_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown component"):
            await mcp_server_module.describe_component_type("TotallyFake")


# ---------------------------------------------------------------------------
# Flow duplication / starter projects
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestDuplicateFlow:
    async def test_duplicate_flow(self):
        created = await mcp_server_module.create_flow("OriginalFlow", "desc")
        await mcp_server_module.add_component(created["id"], "ChatInput")
        dup = await mcp_server_module.duplicate_flow(created["id"], "TheCopy")
        assert dup["name"] == "TheCopy"
        assert dup["id"] != created["id"]
        info = await mcp_server_module.get_flow_info(dup["id"])
        assert info["node_count"] == 1


@pytest.mark.usefixtures("mcp_client")
class TestStarterProjects:
    async def test_list_starter_projects(self):
        starters = await mcp_server_module.list_starter_projects()
        assert isinstance(starters, list)
        assert len(starters) > 0
        assert "name" in starters[0]
        assert "graph" in starters[0]

    async def test_use_starter_project(self):
        starters = await mcp_server_module.list_starter_projects()
        starter_name = starters[0]["name"]
        result = await mcp_server_module.use_starter_project(starter_name, "MyStarter")
        assert result["name"] == "MyStarter"
        info = await mcp_server_module.get_flow_info(result["id"])
        assert info["node_count"] > 0

    async def test_use_starter_project_unknown_raises(self):
        with pytest.raises(ValueError, match="not found"):
            await mcp_server_module.use_starter_project("NonexistentStarter")


# ---------------------------------------------------------------------------
# Graph repr
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mcp_client")
class TestGraphRepr:
    async def test_get_flow_info_includes_graph(self):
        created = await mcp_server_module.create_flow("GraphTest")
        await mcp_server_module.add_component(created["id"], "ChatInput")
        info = await mcp_server_module.get_flow_info(created["id"])
        assert "graph" in info
        assert "ChatInput" in info["graph"]

    async def test_list_flows_includes_graph(self):
        await mcp_server_module.create_flow("GraphListTest")
        flows = await mcp_server_module.list_flows(query="GraphListTest")
        assert len(flows) >= 1
        assert "graph" in flows[0]


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class TestRunFlow:
    async def test_run_simple_flow(self, mcp_client, created_api_key):
        """Build a ChatInput -> ChatOutput flow and run it."""
        # run_flow requires an API key
        mcp_client.api_key = created_api_key.api_key
        created = await mcp_server_module.create_flow("RunTest")
        c1 = await mcp_server_module.add_component(created["id"], "ChatInput")
        c2 = await mcp_server_module.add_component(created["id"], "ChatOutput")
        await mcp_server_module.connect_components(created["id"], c1["id"], "message", c2["id"], "input_value")
        result = await mcp_server_module.run_flow(created["id"], input_value="Hello from test")
        assert isinstance(result, dict)
        assert "outputs" in result
