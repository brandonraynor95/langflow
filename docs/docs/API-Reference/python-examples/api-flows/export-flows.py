import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/flows/download/"

headers = {
    "accept": f"application/json",
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = [
  "e1e40c77-0541-41a9-88ab-ddb3419398b5",
  "92f9a4c5-cfc8-4656-ae63-1f0881163c28"
]

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

with open("langflow-flows.zip", "wb") as f:
    f.write(response.content)
print("Saved response to langflow-flows.zip")
