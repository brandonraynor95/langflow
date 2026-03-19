import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/webhook/{os.getenv('FLOW_ID', '')}"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "data": "example-data"
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
