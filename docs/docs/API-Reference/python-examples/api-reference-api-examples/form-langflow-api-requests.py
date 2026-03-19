import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/run/{os.getenv('FLOW_ID', '')}?stream=false"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "input_value": "hello world!",
  "output_type": "chat",
  "input_type": "chat",
  "tweaks": {
    "ChatOutput-6zcZt": {
      "should_store_message": true
    }
  }
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
