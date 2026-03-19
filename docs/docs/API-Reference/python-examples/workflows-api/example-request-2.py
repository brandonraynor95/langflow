import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v2/workflows/stop"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "job_id": "job_id_1234567890"
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
