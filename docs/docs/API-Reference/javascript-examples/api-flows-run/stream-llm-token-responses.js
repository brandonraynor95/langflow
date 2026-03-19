const payload = {
  message: "Tell me something interesting!",
  session_id: "chat-123"
};

const options = {
  method: 'POST',
  headers: {
    'accept': 'application/json',
    'Content-Type': 'application/json',
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
