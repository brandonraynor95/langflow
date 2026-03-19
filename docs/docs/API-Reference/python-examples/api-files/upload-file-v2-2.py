import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v2/files"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

files = {
    "file": open("FILE_NAME.EXTENSION", "rb"),
}

response = requests.request("POST", url, headers=headers, files=files)
response.raise_for_status()

print(response.text)

for _f in files.values():
    if hasattr(_f, 'close'):
        _f.close()
