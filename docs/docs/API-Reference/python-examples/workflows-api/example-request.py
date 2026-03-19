import os

import requests

url = f"{os.getenv('LANGFLOW_SERVER_URL', '')}/api/v2/workflows?job_id=job_id_1234567890"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("GET", url, headers=headers)
response.raise_for_status()

print(response.text)
