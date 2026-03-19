import requests

url = "http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID"

# Request payload
payload = {
    "input_value": "Tell me about something interesting!",
    "session_id": "chat-123",
    "input_type": "chat",
    "output_type": "chat",
    "output_component": "",
}

# Request headers
headers = {"Content-Type": "application/json", "x-api-key": "LANGFLOW_API_KEY"}

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    print(response.json())
except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
