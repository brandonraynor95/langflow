import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/build/123e4567-e89b-12d3-a456-426614174000/events?stream=false"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("GET", url, headers=headers)
response.raise_for_status()

print(response.text)
