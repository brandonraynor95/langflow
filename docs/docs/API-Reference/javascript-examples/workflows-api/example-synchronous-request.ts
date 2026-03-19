import axios from 'axios';

const url = `${LANGFLOW_SERVER_URL}/api/v2/workflows`;

const payload = {
  flow_id: "flow_67ccd2be17f0819081ff3bb2cf6508e60bb6a6b452d3795b",
  background: false,
  inputs: {
    "ChatInput-abc.input_type": "chat",
    "ChatInput-abc.input_value": "what is 2+2",
    "ChatInput-abc.session_id": "session-123"
  }
};

const runWorkflow = async () => {
  try {
    const response = await axios.post(url, payload, {
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': LANGFLOW_API_KEY
      }
    });
    console.log(response.data);
  } catch (error) {
    console.error('Error triggering workflow:', error);
  }
};

runWorkflow();
