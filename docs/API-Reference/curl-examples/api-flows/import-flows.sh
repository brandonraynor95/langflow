curl -X POST \
  "$LANGFLOW_URL/api/v1/flows/upload/?folder_id=$FOLDER_ID" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -F "file=@agent-with-astra-db-tool.json;type=application/json"
