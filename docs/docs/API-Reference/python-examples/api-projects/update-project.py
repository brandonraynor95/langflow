import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/projects/b408ddb9-6266-4431-9be8-e04a62758331"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "name": "string",
  "description": "string",
  "parent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "components": [
    "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  ],
  "flows": [
    "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  ]
}

response = requests.request("PATCH", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
