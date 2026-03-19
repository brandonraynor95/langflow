curl -X POST \
  "http://$LANGFLOW_SERVER_URL/api/v1/responses" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ced2ec91-f325-4bf0-8754-f3198c2b1563",
    "input": "What'\''s my name?",
    "previous_response_id": "session-alice-1756839048"
  }'
