#!/bin/bash
# watsonx Orchestrate Integration Setup Script
# This script exports your Langflow project and sets up watsonx Orchestrate integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${1:-32b1f197-4565-4ad9-a214-29bc05ae0270}"
LANGFLOW_URL="${2:-http://localhost:7860}"
OUTPUT_DIR="./wxo_export"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}watsonx Orchestrate Integration Setup${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}Project ID:${NC} $PROJECT_ID"
echo -e "${YELLOW}Langflow URL:${NC} $LANGFLOW_URL"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓${NC} Created output directory: $OUTPUT_DIR"

# Check if Langflow is running
echo ""
echo -e "${YELLOW}Checking Langflow connection...${NC}"
if ! curl -s -f "$LANGFLOW_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}✗ ERROR: Cannot connect to Langflow at $LANGFLOW_URL${NC}"
    echo -e "${YELLOW}  Make sure Langflow is running with: make run_cli${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Langflow is running"

# Export full configuration
echo ""
echo -e "${YELLOW}Exporting watsonx Orchestrate configuration...${NC}"
EXPORT_URL="$LANGFLOW_URL/api/v1/wxo/$PROJECT_ID/export?base_url=$LANGFLOW_URL"
if ! curl -s -f "$EXPORT_URL" -o "$OUTPUT_DIR/full_export.json"; then
    echo -e "${RED}✗ ERROR: Failed to export configuration${NC}"
    echo -e "${YELLOW}  URL: $EXPORT_URL${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Exported full configuration to $OUTPUT_DIR/full_export.json"

# Extract and save individual components
echo ""
echo -e "${YELLOW}Extracting configuration components...${NC}"

# Extract toolkit config
python3 -c "import json; data=json.load(open('$OUTPUT_DIR/full_export.json')); json.dump(data['toolkit_config'], open('$OUTPUT_DIR/toolkit_config.json', 'w'), indent=2)"
echo -e "${GREEN}✓${NC} Saved toolkit configuration to $OUTPUT_DIR/toolkit_config.json"

# Extract agent YAML
python3 -c "import json; data=json.load(open('$OUTPUT_DIR/full_export.json')); open('$OUTPUT_DIR/agent.yaml', 'w').write(data['agent_yaml'])"
echo -e "${GREEN}✓${NC} Saved agent YAML to $OUTPUT_DIR/agent.yaml"

# Extract CLI commands
python3 -c "import json; data=json.load(open('$OUTPUT_DIR/full_export.json')); open('$OUTPUT_DIR/import_toolkit.sh', 'w').write('#!/bin/bash\n' + data['cli_import_command'])"
chmod +x "$OUTPUT_DIR/import_toolkit.sh"
echo -e "${GREEN}✓${NC} Saved toolkit import command to $OUTPUT_DIR/import_toolkit.sh"

# Extract setup instructions
python3 -c "import json; data=json.load(open('$OUTPUT_DIR/full_export.json')); open('$OUTPUT_DIR/SETUP_INSTRUCTIONS.md', 'w').write(data['setup_instructions'])"
echo -e "${GREEN}✓${NC} Saved setup instructions to $OUTPUT_DIR/SETUP_INSTRUCTIONS.md"

# Get project info
PROJECT_NAME=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/full_export.json'))['project_name'])")
TOOL_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_DIR/full_export.json'))['toolkit_config']['tools']))")
MCP_URL=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/full_export.json'))['toolkit_config']['mcp_url'])")

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Export Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}Project:${NC} $PROJECT_NAME"
echo -e "${YELLOW}Tools Exported:${NC} $TOOL_COUNT"
echo -e "${YELLOW}MCP URL:${NC} $MCP_URL"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo -e "1. ${YELLOW}Review the setup instructions:${NC}"
echo -e "   cat $OUTPUT_DIR/SETUP_INSTRUCTIONS.md"
echo ""
echo -e "2. ${YELLOW}Install watsonx Orchestrate CLI${NC} (if not already installed):"
echo -e "   https://www.ibm.com/docs/en/watsonx-orchestrate"
echo ""
echo -e "3. ${YELLOW}Import the toolkit:${NC}"
echo -e "   $OUTPUT_DIR/import_toolkit.sh"
echo ""
echo -e "4. ${YELLOW}Create the agent:${NC}"
echo -e "   orchestrate agents create -f $OUTPUT_DIR/agent.yaml"
echo ""
echo -e "5. ${YELLOW}Test your agent:${NC}"
echo -e "   orchestrate agents run ${PROJECT_NAME}_agent --prompt 'Hello!'"
echo ""
echo -e "${GREEN}All configuration files are in: $OUTPUT_DIR/${NC}"
echo ""

# Made with Bob
