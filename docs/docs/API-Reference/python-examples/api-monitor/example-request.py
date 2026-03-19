import os

import requests

base_url = os.getenv("LANGFLOW_SERVER_URL", "http://localhost:7860")
api_key = os.getenv("LANGFLOW_API_KEY")
flow_id = "YOUR_FLOW_ID"

response = requests.get(
    f"{base_url}/api/v1/monitor/traces",
    params={"flow_id": flow_id, "page": 1, "size": 50},
    headers={"x-api-key": api_key, "accept": "application/json"},
    timeout=10,
)
response.raise_for_status()
traces = response.json()
print(traces)
