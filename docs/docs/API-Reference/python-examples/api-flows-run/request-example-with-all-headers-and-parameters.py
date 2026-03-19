import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/run/{os.getenv('FLOW_ID', '')}?stream=true"

headers = {
    "Content-Type": f"application/json",
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "input_value": "Tell me a story",
  "input_type": "chat",
  "output_type": "chat",
  "output_component": "chat_output",
  "session_id": "chat-123",
  "tweaks": {
    "component_id": {
      "parameter_name": "value"
    }
  }
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
