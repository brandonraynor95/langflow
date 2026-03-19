import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/files/download/{os.getenv('FLOW_ID', '')}/2024-12-30_15-19-43_your_file.txt"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("GET", url, headers=headers)
response.raise_for_status()

with open("downloaded_file.txt", "wb") as f:
    f.write(response.content)
print("Saved response to downloaded_file.txt")
