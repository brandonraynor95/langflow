const payload = {
  input_value: "Tell me about something interesting!",
  session_id: "chat-123",
  input_type: "chat",
  output_type: "chat",
  output_component: ""
};

const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': 'LANGFLOW_API_KEY'
  },
  body: JSON.stringify(payload)
};

fetch('http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID', options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
