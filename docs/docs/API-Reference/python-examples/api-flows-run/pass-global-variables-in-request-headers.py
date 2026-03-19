import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/run/{os.getenv('FLOW_ID', '')}"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
    "X-LANGFLOW-GLOBAL-VAR-OPENAI_API_KEY": f"sk-...",
    "X-LANGFLOW-GLOBAL-VAR-USER_ID": f"user123",
    "X-LANGFLOW-GLOBAL-VAR-ENVIRONMENT": f"production",
}

payload = {
  "input_value": "Tell me about something interesting!",
  "input_type": "chat",
  "output_type": "chat"
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
