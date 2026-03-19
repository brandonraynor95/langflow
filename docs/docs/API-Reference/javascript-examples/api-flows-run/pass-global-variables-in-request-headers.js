const payload = {
  input_value: "Tell me about something interesting!",
  input_type: "chat",
  output_type: "chat"
};

const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': 'LANGFLOW_API_KEY',
    'X-LANGFLOW-GLOBAL-VAR-OPENAI_API_KEY': 'sk-...',
    'X-LANGFLOW-GLOBAL-VAR-USER_ID': 'user123',
    'X-LANGFLOW-GLOBAL-VAR-ENVIRONMENT': 'production'
  },
  body: JSON.stringify(payload)
};

fetch('http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID', options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
