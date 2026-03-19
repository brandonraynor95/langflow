import requests

url = f"{LANGFLOW_SERVER_URL}/api/v2/workflows"
params = {"job_id": "job_id_1234567890"}
headers = {"accept": "application/json", "x-api-key": LANGFLOW_API_KEY}

response = requests.get(url, params=params, headers=headers)
print(response.json())
