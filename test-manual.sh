#!/usr/bin/env bash
# Manual A2A smoke test — run against a live Langflow instance.
#
# Usage:
#   1. Start Langflow:  uv run langflow run
#   2. Run this script: bash test-manual.sh
#
# For steps 6-7 (message:send / message:stream), you need a real flow
# with an LLM configured. Build one in the UI with ChatInput → Agent →
# ChatOutput, save it, then set FLOW_ID below before running.
#
# If you just want to test discovery (steps 1-5), the script creates
# a minimal flow via API — no LLM needed.

set -euo pipefail

BASE_URL="${LANGFLOW_URL:-http://localhost:7860}"
USERNAME="${LANGFLOW_USER:-langflow}"
PASSWORD="${LANGFLOW_PASSWORD:-langflow}"
SLUG="manual-test-agent"

# Use an existing flow ID for message:send/stream tests (needs LLM).
# Leave empty to skip those steps.
REAL_FLOW_ID="${REAL_FLOW_ID:-}"

echo "=== A2A Manual Test ==="
echo "Target: $BASE_URL"
echo ""

# -----------------------------------------------------------------
# Step 1: Login
# -----------------------------------------------------------------
echo "--- Step 1: Login ---"
LOGIN_RESPONSE=$(curl -sf -X POST "$BASE_URL/api/v1/login" \
  -d "username=$USERNAME&password=$PASSWORD" 2>&1) || {
  echo "Login failed. Is Langflow running at $BASE_URL?"
  echo "Trying without auth (auto-login mode)..."
  TOKEN=""
}

if [ -n "${LOGIN_RESPONSE:-}" ]; then
  TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
fi

if [ -n "$TOKEN" ]; then
  AUTH_HEADER="Authorization: Bearer $TOKEN"
  echo "Logged in. Token: ${TOKEN:0:20}..."
else
  AUTH_HEADER=""
  echo "Running without auth (auto-login mode)"
fi
echo ""

# -----------------------------------------------------------------
# Step 2: Create a minimal agent flow via API
# -----------------------------------------------------------------
echo "--- Step 2: Create test flow ---"
FLOW_RESPONSE=$(curl -sf -X POST "$BASE_URL/api/v1/flows/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "A2A Manual Test Agent",
    "description": "A test agent for manual A2A verification",
    "data": {
      "nodes": [
        {"id": "ci", "data": {"type": "ChatInput", "node": {"template": {}}}},
        {"id": "ag", "data": {"type": "Agent", "node": {"template": {}}}},
        {"id": "co", "data": {"type": "ChatOutput", "node": {"template": {}}}}
      ],
      "edges": [
        {"source": "ci", "target": "ag"},
        {"source": "ag", "target": "co"}
      ]
    }
  }')

FLOW_ID=$(echo "$FLOW_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created flow: $FLOW_ID"
echo ""

# -----------------------------------------------------------------
# Step 3: Enable A2A on the flow
# -----------------------------------------------------------------
echo "--- Step 3: Enable A2A ---"
CONFIG_RESPONSE=$(curl -sf -X PUT "$BASE_URL/api/v1/flows/$FLOW_ID/a2a-config" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{
    \"a2a_enabled\": true,
    \"a2a_agent_slug\": \"$SLUG\",
    \"a2a_name\": \"Manual Test Agent\",
    \"a2a_description\": \"An agent for manual A2A testing\"
  }")
echo "$CONFIG_RESPONSE" | python3 -m json.tool
echo ""

# -----------------------------------------------------------------
# Step 4: Read back the config
# -----------------------------------------------------------------
echo "--- Step 4: Read A2A config ---"
curl -sf "$BASE_URL/api/v1/flows/$FLOW_ID/a2a-config" \
  -H "$AUTH_HEADER" | python3 -m json.tool
echo ""

# -----------------------------------------------------------------
# Step 5: Discover AgentCard (NO AUTH — public endpoint)
# -----------------------------------------------------------------
echo "--- Step 5: Discover AgentCard (public, no auth) ---"
CARD=$(curl -sf "$BASE_URL/a2a/$SLUG/.well-known/agent-card.json")
echo "$CARD" | python3 -m json.tool

# Validate key fields
echo ""
echo "Validating card fields..."
echo "$CARD" | python3 -c "
import sys, json
card = json.load(sys.stdin)
checks = [
    ('name present', bool(card.get('name'))),
    ('description present', bool(card.get('description'))),
    ('url present', bool(card.get('url'))),
    ('skills present', len(card.get('skills', [])) > 0),
    ('capabilities.streaming', card.get('capabilities', {}).get('streaming') == True),
    ('capabilities.pushNotifications=false', card.get('capabilities', {}).get('pushNotifications') == False),
    ('defaultInputModes has text', 'text' in card.get('defaultInputModes', [])),
    ('defaultOutputModes has text', 'text' in card.get('defaultOutputModes', [])),
]
all_pass = True
for label, ok in checks:
    status = 'PASS' if ok else 'FAIL'
    if not ok: all_pass = False
    print(f'  [{status}] {label}')
print()
print('AgentCard validation:', 'ALL PASSED' if all_pass else 'SOME FAILED')
"
echo ""

# -----------------------------------------------------------------
# Step 6: Extended card (auth required)
# -----------------------------------------------------------------
echo "--- Step 6: Extended AgentCard (auth required) ---"
echo "Without auth (should fail):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/a2a/$SLUG/v1/card")
echo "  HTTP $HTTP_CODE (expected 401 or 403)"

echo "With auth:"
curl -sf "$BASE_URL/a2a/$SLUG/v1/card" \
  -H "$AUTH_HEADER" | python3 -c "
import sys, json
card = json.load(sys.stdin)
print(f'  name: {card[\"name\"]}')
print(f'  extended: {card.get(\"extended\", False)}')
"
echo ""

# -----------------------------------------------------------------
# Step 7: Disable and verify 404
# -----------------------------------------------------------------
echo "--- Step 7: Disable A2A and verify 404 ---"
curl -sf -X PUT "$BASE_URL/api/v1/flows/$FLOW_ID/a2a-config" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"a2a_enabled": false}' > /dev/null

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/a2a/$SLUG/.well-known/agent-card.json")
echo "AgentCard after disable: HTTP $HTTP_CODE (expected 404)"

# Re-enable for message tests
curl -sf -X PUT "$BASE_URL/api/v1/flows/$FLOW_ID/a2a-config" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{\"a2a_enabled\": true, \"a2a_agent_slug\": \"$SLUG\"}" > /dev/null
echo "Re-enabled for message tests."
echo ""

# -----------------------------------------------------------------
# Step 8: message:send (needs real flow with LLM)
# -----------------------------------------------------------------
if [ -n "$REAL_FLOW_ID" ]; then
  REAL_SLUG="real-test-agent"
  curl -sf -X PUT "$BASE_URL/api/v1/flows/$REAL_FLOW_ID/a2a-config" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"a2a_enabled\": true, \"a2a_agent_slug\": \"$REAL_SLUG\"}" > /dev/null

  echo "--- Step 8: message:send (real flow) ---"
  curl -sf -X POST "$BASE_URL/a2a/$REAL_SLUG/v1/message:send" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d '{
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What can you help me with?"}],
        "contextId": "manual-test-ctx"
      }
    }' | python3 -m json.tool
  echo ""

  echo "--- Step 9: message:stream (real flow) ---"
  echo "(Streaming output — press Ctrl+C to stop)"
  curl -N -X POST "$BASE_URL/a2a/$REAL_SLUG/v1/message:stream" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d '{
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Tell me about yourself in 2 sentences."}],
        "contextId": "manual-test-ctx"
      }
    }'
  echo ""
else
  echo "--- Steps 8-9: Skipped (no REAL_FLOW_ID set) ---"
  echo "To test message:send/stream, build a flow in the UI with an LLM,"
  echo "then run:  REAL_FLOW_ID=<your-flow-id> bash test-manual.sh"
  echo ""
fi

# -----------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------
echo "--- Cleanup ---"
curl -sf -X DELETE "$BASE_URL/api/v1/flows/$FLOW_ID" \
  -H "$AUTH_HEADER" > /dev/null 2>&1 || true
echo "Deleted test flow $FLOW_ID"
echo ""
echo "=== Done ==="
