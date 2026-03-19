curl -X POST \
  "$LANGFLOW_URL/api/v1/projects/upload/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -F "file=@20241230_135006_langflow_flows.zip;type=application/zip"
