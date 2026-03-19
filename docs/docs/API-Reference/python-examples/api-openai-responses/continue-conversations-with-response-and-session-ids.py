import os

import requests

url = f"http://{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/responses"

headers = {
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
    "Content-Type": f"application/json",
}

payload = {
  "model": "$FLOW_ID",
  "input": "Hello, my name is Alice"
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
