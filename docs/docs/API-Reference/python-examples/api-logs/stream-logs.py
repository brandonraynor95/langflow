import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/logs-stream"

headers = {
    "accept": f"text/event-stream",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("GET", url, headers=headers)
response.raise_for_status()

print(response.text)
