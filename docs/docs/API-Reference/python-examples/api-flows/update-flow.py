import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/flows/{os.getenv('FLOW_ID', '')}"

headers = {
    "accept": f"application/json",
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "name": "string",
  "description": "string",
  "data": {},
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "endpoint_name": "my_new_endpoint_name",
  "locked": true
}

response = requests.request("PATCH", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
