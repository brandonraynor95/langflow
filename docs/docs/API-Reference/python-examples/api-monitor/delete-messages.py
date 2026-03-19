import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/monitor/messages"

headers = {
    "accept": f"*/*",
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = [
  "MESSAGE_ID_1",
  "MESSAGE_ID_2"
]

response = requests.request("DELETE", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
