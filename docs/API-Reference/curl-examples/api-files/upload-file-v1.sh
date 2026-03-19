curl -X POST \
  "$LANGFLOW_URL/api/v1/files/upload/$FLOW_ID" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -F "file=@FILE_NAME.txt"
