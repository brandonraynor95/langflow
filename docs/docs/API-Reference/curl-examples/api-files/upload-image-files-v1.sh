curl -X POST "$LANGFLOW_URL/api/v1/files/upload/$FLOW_ID" \
  -H "Content-Type: multipart/form-data" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -F "file=@PATH/TO/FILE.png"
