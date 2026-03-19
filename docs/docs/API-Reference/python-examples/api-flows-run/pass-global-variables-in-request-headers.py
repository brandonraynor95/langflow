import requests

url = "http://LANGFLOW_SERVER_URL/api/v1/run/FLOW_ID"

# Request payload
payload = {"input_value": "Tell me about something interesting!", "input_type": "chat", "output_type": "chat"}

# Request headers with global variables
headers = {
    "Content-Type": "application/json",
    "x-api-key": "LANGFLOW_API_KEY",
    "X-LANGFLOW-GLOBAL-VAR-OPENAI_API_KEY": "sk-...",
    "X-LANGFLOW-GLOBAL-VAR-USER_ID": "user123",
    "X-LANGFLOW-GLOBAL-VAR-ENVIRONMENT": "production",
}

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    print(response.json())
except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
