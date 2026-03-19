import os

import requests

url = f"http://{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/responses"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "model": "FLOW_ID",
  "input": "Calculate 23 * 15 and show me the result",
  "stream": false,
  "include": [
    "tool_call.results"
  ]
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
