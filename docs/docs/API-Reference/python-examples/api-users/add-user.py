import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/users/"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "username": "newuser2",
  "password": "securepassword123"
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
