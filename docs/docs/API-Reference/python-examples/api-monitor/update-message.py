import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/monitor/messages/3ab66cc6-c048-48f8-ab07-570f5af7b160"

headers = {
    "accept": f"application/json",
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "text": "testing 1234"
}

response = requests.request("PUT", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
