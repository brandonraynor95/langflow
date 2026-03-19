import requests

url = "http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID?stream=true"

# Request payload
payload = {"message": "Tell me something interesting!", "session_id": "chat-123"}

# Request headers
headers = {"accept": "application/json", "Content-Type": "application/json", "x-api-key": "LANGFLOW_API_KEY"}

try:
    response = requests.post(url, json=payload, headers=headers, stream=True)
    response.raise_for_status()

    # Process streaming response
    for line in response.iter_lines():
        if line:
            print(line.decode("utf-8"))
except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
