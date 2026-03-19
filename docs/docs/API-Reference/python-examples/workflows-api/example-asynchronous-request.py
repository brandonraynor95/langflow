import requests

url = f"{LANGFLOW_SERVER_URL}/api/v2/workflows"
headers = {"Content-Type": "application/json", "x-api-key": LANGFLOW_API_KEY}

payload = {
    "flow_id": "flow_67ccd2be17f0819081ff3bb2cf6508e60bb6a6b452d3795b",
    "background": True,
    "stream": False,
    "inputs": {
        "ChatInput-abc.input_type": "chat",
        "ChatInput-abc.input_value": "Process this in the background",
        "ChatInput-abc.session_id": "session-456",
    },
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())  # Returns job_id immediately
