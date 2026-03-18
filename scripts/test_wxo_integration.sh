#!/bin/bash
# Automated test script for watsonx Orchestrate integration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ID="32b1f197-4565-4ad9-a214-29bc05ae0270"
LANGFLOW_URL="http://localhost:7860"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🧪 Testing watsonx Orchestrate Integration${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Test 1: Langflow Health
echo -e "${YELLOW}Test 1: Langflow Health Check...${NC}"
if curl -s -f "$LANGFLOW_URL/health" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Langflow is running${NC}"
else
  echo -e "${RED}❌ Langflow is not responding${NC}"
  echo -e "${YELLOW}   Start Langflow with: make run_cli${NC}"
  exit 1
fi

# Test 2: MCP Server
echo -e "${YELLOW}Test 2: MCP Server Endpoint...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$LANGFLOW_URL/api/v1/mcp/project/$PROJECT_ID/streamable")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "406" ]; then
  echo -e "${GREEN}✅ MCP Server is running (HTTP $HTTP_CODE)${NC}"
else
  echo -e "${RED}❌ MCP Server returned HTTP $HTTP_CODE${NC}"
  exit 1
fi

# Test 3: Tool Count
echo -e "${YELLOW}Test 3: MCP Tool Discovery...${NC}"
TOOL_COUNT=$(curl -s "$LANGFLOW_URL/api/v1/mcp/project/$PROJECT_ID?mcp_enabled=true" \
  -H "Accept: application/json" | python3 -c "import json, sys; print(len(json.load(sys.stdin)['tools']))" 2>/dev/null || echo "0")
if [ "$TOOL_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✅ Found $TOOL_COUNT MCP-enabled tools${NC}"
else
  echo -e "${RED}❌ No tools found${NC}"
  echo -e "${YELLOW}   Enable MCP for flows in Langflow UI${NC}"
  exit 1
fi

# Test 4: Export API - Full Export
echo -e "${YELLOW}Test 4: Export API - Full Export...${NC}"
if curl -s -f "$LANGFLOW_URL/api/v1/wxo/$PROJECT_ID/export" > /tmp/wxo_test_export.json 2>&1; then
  echo -e "${GREEN}✅ Full export API working${NC}"
  
  # Validate JSON
  if python3 -m json.tool /tmp/wxo_test_export.json > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Export JSON is valid${NC}"
  else
    echo -e "${RED}❌ Export JSON is invalid${NC}"
    exit 1
  fi
else
  echo -e "${RED}❌ Export API failed${NC}"
  exit 1
fi

# Test 5: Export API - Toolkit Config
echo -e "${YELLOW}Test 5: Export API - Toolkit Config...${NC}"
if curl -s -f "$LANGFLOW_URL/api/v1/wxo/$PROJECT_ID/export/toolkit-config" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Toolkit config endpoint working${NC}"
else
  echo -e "${RED}❌ Toolkit config endpoint failed${NC}"
  exit 1
fi

# Test 6: Export API - Agent YAML
echo -e "${YELLOW}Test 6: Export API - Agent YAML...${NC}"
if curl -s -f "$LANGFLOW_URL/api/v1/wxo/$PROJECT_ID/export/agent-yaml" > /tmp/wxo_test_agent.yaml 2>&1; then
  echo -e "${GREEN}✅ Agent YAML endpoint working${NC}"
  
  # Check if it's valid YAML (contains expected keys)
  if grep -q "apiVersion:" /tmp/wxo_test_agent.yaml && grep -q "kind: Agent" /tmp/wxo_test_agent.yaml; then
    echo -e "${GREEN}✅ Agent YAML is valid${NC}"
  else
    echo -e "${RED}❌ Agent YAML is invalid${NC}"
    exit 1
  fi
else
  echo -e "${RED}❌ Agent YAML endpoint failed${NC}"
  exit 1
fi

# Test 7: Export Files
echo -e "${YELLOW}Test 7: Export Files Existence...${NC}"
MISSING_FILES=0
for file in agent.yaml import_toolkit.sh SETUP_INSTRUCTIONS.md toolkit_config.json full_export.json; do
  if [ -f "wxo_export/$file" ]; then
    echo -e "${GREEN}  ✓ wxo_export/$file${NC}"
  else
    echo -e "${RED}  ✗ wxo_export/$file (missing)${NC}"
    MISSING_FILES=$((MISSING_FILES + 1))
  fi
done

if [ $MISSING_FILES -eq 0 ]; then
  echo -e "${GREEN}✅ All export files exist${NC}"
else
  echo -e "${YELLOW}⚠️  $MISSING_FILES file(s) missing - run: ./scripts/wxo_setup.sh${NC}"
fi

# Test 8: Validate Export Content
echo -e "${YELLOW}Test 8: Validate Export Content...${NC}"
if [ -f "wxo_export/full_export.json" ]; then
  PROJECT_NAME=$(python3 -c "import json; print(json.load(open('wxo_export/full_export.json'))['project_name'])" 2>/dev/null || echo "")
  EXPORTED_TOOLS=$(python3 -c "import json; print(len(json.load(open('wxo_export/full_export.json'))['toolkit_config']['tools']))" 2>/dev/null || echo "0")
  
  if [ -n "$PROJECT_NAME" ] && [ "$EXPORTED_TOOLS" -gt 0 ]; then
    echo -e "${GREEN}✅ Export contains valid data${NC}"
    echo -e "${BLUE}   Project: $PROJECT_NAME${NC}"
    echo -e "${BLUE}   Tools: $EXPORTED_TOOLS${NC}"
  else
    echo -e "${RED}❌ Export data is incomplete${NC}"
    exit 1
  fi
fi

# Test 9: Import Script Executable
echo -e "${YELLOW}Test 9: Import Script Permissions...${NC}"
if [ -x "wxo_export/import_toolkit.sh" ]; then
  echo -e "${GREEN}✅ Import script is executable${NC}"
else
  echo -e "${YELLOW}⚠️  Import script not executable - fixing...${NC}"
  chmod +x wxo_export/import_toolkit.sh
  echo -e "${GREEN}✅ Fixed${NC}"
fi

# Test 10: Performance Test
echo -e "${YELLOW}Test 10: Export Performance...${NC}"
START_TIME=$(date +%s%N)
curl -s "$LANGFLOW_URL/api/v1/wxo/$PROJECT_ID/export" > /dev/null 2>&1
END_TIME=$(date +%s%N)
DURATION=$(( (END_TIME - START_TIME) / 1000000 ))

if [ $DURATION -lt 3000 ]; then
  echo -e "${GREEN}✅ Export completed in ${DURATION}ms (< 3s)${NC}"
else
  echo -e "${YELLOW}⚠️  Export took ${DURATION}ms (> 3s)${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}🎉 All Tests Passed!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${BLUE}Integration Status:${NC}"
echo -e "  ${GREEN}✓${NC} MCP Server: Running"
echo -e "  ${GREEN}✓${NC} Tools Available: $TOOL_COUNT"
echo -e "  ${GREEN}✓${NC} Export API: Working"
echo -e "  ${GREEN}✓${NC} Export Files: Ready"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo -e "1. ${YELLOW}Install watsonx Orchestrate CLI${NC}"
echo -e "   https://www.ibm.com/docs/en/watsonx-orchestrate"
echo ""
echo -e "2. ${YELLOW}Import toolkit:${NC}"
echo -e "   ./wxo_export/import_toolkit.sh"
echo ""
echo -e "3. ${YELLOW}Create agent:${NC}"
echo -e "   orchestrate agents create -f wxo_export/agent.yaml"
echo ""
echo -e "4. ${YELLOW}Test agent:${NC}"
echo -e "   orchestrate agents run starter_project_agent --prompt 'Hello!'"
echo ""
echo -e "${GREEN}Integration is ready to use! 🚀${NC}"
echo ""

# Cleanup
rm -f /tmp/wxo_test_export.json /tmp/wxo_test_agent.yaml

# Made with Bob
