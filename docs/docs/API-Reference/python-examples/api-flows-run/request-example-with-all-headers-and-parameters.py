import requests

url = "http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID?stream=true"

# Request payload with tweaks
payload = {
    "input_value": "Tell me a story",
    "input_type": "chat",
    "output_type": "chat",
    "output_component": "chat_output",
    "session_id": "chat-123",
    "tweaks": {"component_id": {"parameter_name": "value"}},
}

# Request headers
headers = {"Content-Type": "application/json", "accept": "application/json", "x-api-key": "LANGFLOW_API_KEY"}

try:
    response = requests.post(url, json=payload, headers=headers, stream=True)
    response.raise_for_status()

    # Process streaming response
    for line in response.iter_lines():
        if line:
            print(line.decode("utf-8"))
except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
