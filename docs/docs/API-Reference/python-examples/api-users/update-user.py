import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/users/10c1c6a2-ab8a-4748-8700-0e4832fd5ce8"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "is_active": true,
  "is_superuser": true
}

response = requests.request("PATCH", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
