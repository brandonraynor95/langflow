import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/users/10c1c6a2-ab8a-4748-8700-0e4832fd5ce8"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("DELETE", url, headers=headers)
response.raise_for_status()

print(response.text)
