import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/run/{os.getenv('FLOW_ID', '')}"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "input_value": "Tell me about something interesting!",
  "session_id": "chat-123",
  "input_type": "chat",
  "output_type": "chat",
  "output_component": ""
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
