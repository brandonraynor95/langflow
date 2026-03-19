import requests

url = f"{LANGFLOW_SERVER_URL}/api/v2/workflows/stop"
headers = {"Content-Type": "application/json", "x-api-key": LANGFLOW_API_KEY}
payload = {"job_id": "job_id_1234567890"}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
