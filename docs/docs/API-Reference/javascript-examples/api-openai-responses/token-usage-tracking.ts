import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "LANGFLOW_SERVER_URL/api/v1/",
  defaultHeaders: {
    "x-api-key": "LANGFLOW_API_KEY"
  },
  apiKey: "dummy-api-key"
});

const response = await client.responses.create({
  model: "FLOW_ID",
  input: "Explain quantum computing in simple terms"
});

// Access token usage if available
if (response.usage) {
  console.log(`Prompt tokens: ${response.usage.prompt_tokens || 0}`);
  console.log(`Completion tokens: ${response.usage.completion_tokens || 0}`);
  console.log(`Total tokens: ${response.usage.total_tokens || 0}`);
} else {
  console.log("Token usage not available for this flow");
}
