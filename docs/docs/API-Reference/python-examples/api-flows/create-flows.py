import os

import requests

url = f"{os.getenv('LANGFLOW_URL', '')}/api/v1/flows/batch/"

headers = {
    "accept": f"application/json",
    "Content-Type": f"application/json",
    "x-api-key": f"{os.getenv('LANGFLOW_API_KEY', '')}",
}

payload = {
  "flows": [
    {
      "name": "string",
      "description": "string",
      "icon": "string",
      "icon_bg_color": "string",
      "gradient": "string",
      "data": {},
      "is_component": false,
      "updated_at": "2024-12-30T18:36:02.737Z",
      "webhook": false,
      "endpoint_name": "string",
      "tags": [
        "string"
      ],
      "locked": false,
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    },
    {
      "name": "string",
      "description": "string",
      "icon": "string",
      "icon_bg_color": "string",
      "gradient": "string",
      "data": {},
      "is_component": false,
      "updated_at": "2024-12-30T18:36:02.737Z",
      "webhook": false,
      "endpoint_name": "string",
      "tags": [
        "string"
      ],
      "locked": false,
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  ]
}

response = requests.request("POST", url, headers=headers, json=payload)
response.raise_for_status()

print(response.text)
