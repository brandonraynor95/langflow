import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/monitor/messages/session/01ce083d-748b-4b8d-97b6-33adbb6a528a?new_session_id=different_session_id"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("PATCH", url, headers=headers)
response.raise_for_status()

print(response.text)
