# watsonx Orchestrate Integration Setup

## Prerequisites
1. Install watsonx Orchestrate CLI: https://www.ibm.com/docs/en/watsonx-orchestrate
2. Authenticate: `orchestrate login`
3. Ensure Langflow is running at http://localhost:7860

## Step 1: Import Toolkit
Run this command to import all 62 tools from the "Starter Project" project:

```bash
orchestrate toolkits add \
  --name starter_project \
  --type mcp \
  --url http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
```

## Step 2: Verify Toolkit
```bash
orchestrate toolkits list
orchestrate toolkits describe starter_project
```

## Step 3: Create Agent
Save the agent YAML configuration to a file (e.g., `starter_project_agent.yaml`), then:

```bash
orchestrate agents create -f starter_project_agent.yaml
```

## Step 4: Test Agent
```bash
orchestrate agents run starter_project_agent --prompt "Hello, what can you help me with?"
```

## Available Tools
1. **basic_prompting**: Perform basic prompting with an OpenAI model.
2. **document_qa**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
3. **document_qa_1**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
4. **document_qa_2**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
5. **document_qa_3**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
6. **document_qa_4**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
7. **document_qa_5**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
8. **document_qa_6**: Integrates PDF reading with a language model to answer document-specific questions. Ideal for small-scale texts, it facilitates direct queries with immediate insights.
9. **new_flow**: Catalyzing Business Growth through Conversational AI.
10. **new_flow_1**: Unleashing Linguistic Creativity.
11. **new_flow_2**: The Power of Language at Your Fingertips.
12. **new_flow_3**: Unleashing Business Potential through Language Engineering.
13. **new_flow_4**: Craft Meaningful Interactions, Generate Value.
14. **new_flow_5**: Maximize Impact with Intelligent Conversations.
15. **new_flow_6**: Craft Meaningful Interactions, Generate Value.
16. **new_flow_7**: Powerful Prompts, Perfectly Positioned.
17. **new_flow_8**: Maximize Impact with Intelligent Conversations.
18. **new_flow_9**: Innovation in Interaction, Revolution in Revenue.
19. **new_flow_10**: Unfolding Linguistic Possibilities.
20. **new_flow_11**: Language Architect at Work!
21. **basic_prompting_backup**: Perform basic prompting with an OpenAI model.
22. **basic_prompting_backup_1**: Perform basic prompting with an OpenAI model.
23. **basic_prompting_backup_backup**: Perform basic prompting with an OpenAI model.
24. **basic_prompting_1**: Perform basic prompting with an OpenAI model.
25. **basic_prompting_2**: Perform basic prompting with an OpenAI model.
26. **basic_prompting_3**: Perform basic prompting with an OpenAI model.
27. **basic_prompting_4**: Perform basic prompting with an OpenAI model.
28. **basic_prompting_5**: Perform basic prompting with an OpenAI model.
29. **basic_prompting_6**: Perform basic prompting with an OpenAI model.
30. **basic_prompting_7**: Perform basic prompting with an OpenAI model.
31. **basic_prompting_8**: Perform basic prompting with an OpenAI model.
32. **basic_prompting_9**: Perform basic prompting with an OpenAI model.
33. **basic_prompting_10**: Perform basic prompting with an OpenAI model.
34. **basic_prompting_11**: Perform basic prompting with an OpenAI model.
35. **basic_prompting_12**: Perform basic prompting with an OpenAI model.
36. **basic_prompting_13**: Perform basic prompting with an OpenAI model.
37. **basic_prompting_14**: Perform basic prompting with an OpenAI model.
38. **basic_prompting_15**: Perform basic prompting with an OpenAI model.
39. **basic_prompting_16**: Perform basic prompting with an OpenAI model.
40. **basic_prompting_17**: Perform basic prompting with an OpenAI model.
41. **basic_prompting_18**: Perform basic prompting with an OpenAI model.
42. **basic_prompting_19**: Perform basic prompting with an OpenAI model.
43. **basic_prompting_20**: Perform basic prompting with an OpenAI model.
44. **basic_prompting_21**: Perform basic prompting with an OpenAI model.
45. **basic_prompting_22**: Perform basic prompting with an OpenAI model.
46. **basic_prompting_23**: Perform basic prompting with an OpenAI model.
47. **basic_prompting_24**: Perform basic prompting with an OpenAI model.
48. **basic_prompting_25**: Perform basic prompting with an OpenAI model.
49. **basic_prompting_26**: Perform basic prompting with an OpenAI model.
50. **basic_prompting_27**: Perform basic prompting with an OpenAI model.
51. **basic_prompting_28**: Perform basic prompting with an OpenAI model.
52. **basic_prompting_29**: Perform basic prompting with an OpenAI model.
53. **basic_prompting_30**: Perform basic prompting with an OpenAI model.
54. **basic_prompting_31**: Perform basic prompting with an OpenAI model.
55. **basic_prompting_32**: Perform basic prompting with an OpenAI model.
56. **basic_prompting_33**: Perform basic prompting with an OpenAI model.
57. **basic_prompting_34**: Perform basic prompting with an OpenAI model.
58. **basic_prompting_35**: Perform basic prompting with an OpenAI model.
59. **basic_prompting_36**: Perform basic prompting with an OpenAI model.
60. **basic_prompting_37**: Perform basic prompting with an OpenAI model.
61. **basic_prompting_38**: Perform basic prompting with an OpenAI model.
62. **simple_agent**: A simple but powerful starter agent.

## Next Steps
- Customize the agent's system prompt in the YAML file
- Add more flows to your Langflow project and re-export
- Create multiple agents with different tool combinations
- Deploy agents to production watsonx Orchestrate environment

## Troubleshooting
- If toolkit import fails, verify Langflow is accessible at http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
- Check that all flows have MCP enabled in Langflow UI
- Ensure watsonx Orchestrate CLI is properly authenticated
