from openai import OpenAI

client = OpenAI(
    base_url="LANGFLOW_SERVER_URL/api/v1/",
    default_headers={"x-api-key": "LANGFLOW_API_KEY"},
    api_key="dummy-api-key",  # Required by OpenAI SDK but not used by Langflow
)

response = client.responses.create(
    model="FLOW_ID",
    input="There is an event that happens on the second wednesday of every month. What are the event dates in 2026?",
)

print(response.output_text)
