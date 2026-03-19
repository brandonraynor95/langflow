import axios from 'axios';

const jobId = 'job_id_1234567890';
const url = `${LANGFLOW_SERVER_URL}/api/v2/workflows`;

const getWorkflowStatus = async () => {
  try {
    const response = await axios.get(url, {
      params: {
        job_id: jobId
      },
      headers: {
        'accept': 'application/json',
        'x-api-key': LANGFLOW_API_KEY
      }
    });
    console.log(response.data);
  } catch (error) {
    console.error('Error getting workflow status:', error);
  }
};

getWorkflowStatus();
