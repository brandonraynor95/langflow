curl -X POST \
  "$LANGFLOW_URL/api/v2/files" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -F "file=@FILE_NAME.EXTENSION"
