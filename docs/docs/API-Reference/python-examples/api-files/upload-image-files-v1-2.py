import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/run/a430cc57-06bb-4c11-be39-d3d4de68d2c4?stream=false"

headers = {
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "output_type": "chat",
  "input_type": "chat",
  "tweaks": {
    "ChatInput-b67sL": {
      "files": "a430cc57-06bb-4c11-be39-d3d4de68d2c4/2024-11-27_14-47-50_image-file.png",
      "input_value": "describe this image"
    }
  }
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
