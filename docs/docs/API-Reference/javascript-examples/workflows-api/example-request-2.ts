import axios from 'axios';

const url = `${LANGFLOW_SERVER_URL}/api/v2/workflows/stop`;

const payload = {
  job_id: "job_id_1234567890"
};

const stopWorkflow = async () => {
  try {
    const response = await axios.post(url, payload, {
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': LANGFLOW_API_KEY
      }
    });
    console.log(response.data);
  } catch (error) {
    console.error('Error stopping workflow:', error);
  }
};

stopWorkflow();
