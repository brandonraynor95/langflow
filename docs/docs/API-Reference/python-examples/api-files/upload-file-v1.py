import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/files/upload/{os.getenv('FLOW_ID', '')}"

headers = {
    "accept": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

files = {
    "file": open("FILE_NAME.txt", "rb"),
}

response = requests.request("POST", url, headers=headers, files=files)
response.raise_for_status()

print(response.text)

for _f in files.values():
    if hasattr(_f, 'close'):
        _f.close()
