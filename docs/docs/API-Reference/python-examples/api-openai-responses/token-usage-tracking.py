from openai import OpenAI

client = OpenAI(
    base_url="LANGFLOW_SERVER_URL/api/v1/", default_headers={"x-api-key": "LANGFLOW_API_KEY"}, api_key="dummy-api-key"
)

response = client.responses.create(model="FLOW_ID", input="Explain quantum computing in simple terms")

# Access token usage if available
if response.usage:
    print(f"Prompt tokens: {response.usage.get('prompt_tokens', 0)}")
    print(f"Completion tokens: {response.usage.get('completion_tokens', 0)}")
    print(f"Total tokens: {response.usage.get('total_tokens', 0)}")
else:
    print("Token usage not available for this flow")
