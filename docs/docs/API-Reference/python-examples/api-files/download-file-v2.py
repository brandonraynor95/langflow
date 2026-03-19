import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v2/files/c7b22c4c-d5e0-4ec9-af97-5d85b7657a34"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

response = requests.request("GET", url, headers=headers)
response.raise_for_status()

with open("downloaded_file.txt", "wb") as f:
    f.write(response.content)
print("Saved response to downloaded_file.txt")
