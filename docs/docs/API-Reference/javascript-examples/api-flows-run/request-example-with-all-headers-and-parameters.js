const payload = {
  input_value: "Tell me a story",
  input_type: "chat",
  output_type: "chat",
  output_component: "chat_output",
  session_id: "chat-123",
  tweaks: {
    component_id: {
      parameter_name: "value"
    }
  }
};

const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'accept': 'application/json',
    'x-api-key': 'LANGFLOW_API_KEY'
  },
  body: JSON.stringify(payload)
};

fetch('http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID?stream=true', options)
  .then(async response => {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        console.log(decoder.decode(value));
      }
    }
  })
  .catch(err => console.error(err));
