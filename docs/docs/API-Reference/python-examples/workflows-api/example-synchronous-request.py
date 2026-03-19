import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v2/workflows"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "flow_id": "flow_67ccd2be17f0819081ff3bb2cf6508e60bb6a6b452d3795b",
  "background": false,
  "inputs": {
    "ChatInput-abc.input_type": "chat",
    "ChatInput-abc.input_value": "what is 2+2",
    "ChatInput-abc.session_id": "session-123"
  }
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
