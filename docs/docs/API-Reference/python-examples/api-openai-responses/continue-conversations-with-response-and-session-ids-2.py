import os

import requests

url = f"http://{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v1/responses"

headers = {
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
    "Content-Type": f"application/json",
}

payload = {
  "model": "ced2ec91-f325-4bf0-8754-f3198c2b1563",
  "input": "What's my name?",
  "previous_response_id": "c45f4ac8-772b-4675-8551-c560b1afd590"
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
