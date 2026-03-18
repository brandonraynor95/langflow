# User Journey: From Langflow to watsonx Orchestrate

## Complete End-to-End Workflow

This document explains **exactly what happens** after a user exports their Langflow project and how they use it in watsonx Orchestrate.

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: BUILD in Langflow                                       │
│ User creates AI workflows visually                              │
│ - Drag and drop components                                      │
│ - Connect LLMs, tools, data sources                             │
│ - Test flows in Langflow UI                                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: EXPORT from Langflow                                    │
│ User exports project to watsonx Orchestrate                     │
│ - Run: ./scripts/wxo_setup.sh                                   │
│ - Gets: toolkit config, agent YAML, import commands             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: IMPORT to watsonx Orchestrate                           │
│ User imports Langflow tools as a toolkit                        │
│ - Run: ./wxo_export/import_toolkit.sh                           │
│ - watsonx Orchestrate now has access to all 62 Langflow tools   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: CREATE AGENT in watsonx Orchestrate                     │
│ User creates an AI agent that uses Langflow tools               │
│ - Run: orchestrate agents create -f wxo_export/agent.yaml       │
│ - Agent can now call any of the 62 Langflow flows               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: USE AGENT in Production                                 │
│ End users interact with the agent                               │
│ - Via Slack, Teams, web chat, API                               │
│ - Agent uses Langflow flows to accomplish tasks                 │
│ - Connects to enterprise systems (SAP, Salesforce, etc.)        │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Step-by-Step Journey

### Step 1: Developer Builds Flows in Langflow

**What the developer does:**

1. Opens Langflow UI (http://localhost:7860)
2. Creates flows visually:
   - **Example Flow 1:** "Customer Support Agent"
     - Input: Customer question
     - RAG: Search knowledge base
     - LLM: Generate answer
     - Output: Response
   - **Example Flow 2:** "Document Q&A"
     - Input: PDF file + question
     - Parse: Extract text from PDF
     - LLM: Answer question about document
     - Output: Answer

3. Tests flows in Langflow playground
4. Enables MCP for flows (makes them available as tools)

**Result:** Working AI workflows ready to be used as tools

---

### Step 2: Developer Exports to watsonx Orchestrate

**What the developer does:**

```bash
# Run the export script
./scripts/wxo_setup.sh
```

**What happens:**

1. Script calls Langflow API
2. Generates export package in `wxo_export/` folder:
   ```
   wxo_export/
   ├── agent.yaml              # Agent configuration
   ├── toolkit_config.json     # Toolkit metadata
   ├── import_toolkit.sh       # Import command
   ├── full_export.json        # Complete export
   └── SETUP_INSTRUCTIONS.md   # Instructions
   ```

**What the developer gets:**

- **Toolkit Config:** Tells watsonx Orchestrate where to find the tools
- **Agent YAML:** Pre-configured agent that uses all the tools
- **Import Commands:** Ready-to-run commands
- **Instructions:** Step-by-step guide

**Result:** Export package ready to import into watsonx Orchestrate

---

### Step 3: Developer Imports Toolkit to watsonx Orchestrate

**What the developer does:**

```bash
# Import the toolkit
./wxo_export/import_toolkit.sh
```

**What this command does:**

```bash
orchestrate toolkits add \
  --name starter_project \
  --type mcp \
  --url http://localhost:7860/api/v1/mcp/project/32b1f197-4565-4ad9-a214-29bc05ae0270/streamable
```

**What happens in watsonx Orchestrate:**

1. watsonx Orchestrate connects to Langflow's MCP server
2. Discovers all 62 tools (flows) available
3. Registers them as a toolkit called "starter_project"
4. Tools are now available to use in agents

**How to verify:**

```bash
# List all toolkits
orchestrate toolkits list

# See the tools in your toolkit
orchestrate toolkits describe starter_project
```

**Result:** watsonx Orchestrate can now call your Langflow flows as tools

---

### Step 4: Developer Creates Agent in watsonx Orchestrate

**What the developer does:**

```bash
# Create an agent using the exported YAML
orchestrate agents create -f wxo_export/agent.yaml
```

**What's in the agent.yaml:**

```yaml
apiVersion: orchestrate.ibm.com/v1
kind: Agent
metadata:
  name: starter_project_agent
spec:
  description: AI agent powered by Starter Project Langflow project
  tools:
    - basic_prompting
    - document_qa
    - simple_agent
    # ... all 62 tools
  systemPrompt: |
    You are an AI assistant with access to 62 tools.
    Use these tools to help users accomplish their tasks.
```

**What happens:**

1. watsonx Orchestrate creates an AI agent
2. Agent has access to all 62 Langflow tools
3. Agent can decide which tools to use based on user requests
4. Agent can chain multiple tools together

**How to verify:**

```bash
# List all agents
orchestrate agents list

# Test the agent
orchestrate agents run starter_project_agent --prompt "Hello, what can you do?"
```

**Result:** Production-ready AI agent that uses your Langflow flows

---

### Step 5: End Users Use the Agent

**Scenario 1: Employee Uses Agent via Slack**

1. **Employee asks in Slack:**

   ```
   @agent Can you analyze this PDF and tell me the key points?
   [uploads document.pdf]
   ```

2. **Agent thinks:**
   - "User wants PDF analysis"
   - "I have a 'document_qa' tool from Langflow"
   - "I'll use that tool"

3. **Agent calls Langflow:**

   ```
   POST http://localhost:7860/api/v1/mcp/project/.../streamable
   Tool: document_qa
   Input: {file: document.pdf, question: "key points"}
   ```

4. **Langflow executes the flow:**
   - Parses PDF
   - Extracts text
   - Sends to LLM
   - Returns key points

5. **Agent responds in Slack:**
   ```
   Here are the key points from the document:
   1. Revenue increased 25%
   2. New product launch in Q3
   3. Expansion to 5 new markets
   ```

**Scenario 2: Customer Service Agent**

1. **Customer asks:**

   ```
   "Why is my order #12345 delayed?"
   ```

2. **Agent workflow:**
   - Uses `basic_prompting` tool to understand question
   - Uses `order_lookup` tool (Langflow flow) to check order status
   - Uses `generate_response` tool to create friendly explanation

3. **Customer gets answer:**
   ```
   Your order #12345 is delayed due to weather conditions.
   Expected delivery: March 20th.
   We've applied a 10% discount to your account.
   ```

**Scenario 3: HR Assistant**

1. **Employee asks:**

   ```
   "How many vacation days do I have left?"
   ```

2. **Agent workflow:**
   - Uses `hr_policy_lookup` tool (Langflow flow with RAG)
   - Uses `employee_data_query` tool (Langflow flow connected to HR system)
   - Combines information and responds

3. **Employee gets answer:**
   ```
   You have 12 vacation days remaining this year.
   Your next scheduled vacation is April 15-19 (5 days).
   ```

---

## Real-World Use Cases

### Use Case 1: Enterprise Customer Support

**Setup:**

1. Developer builds in Langflow:
   - Knowledge base RAG flow
   - Ticket creation flow
   - Order lookup flow
   - Refund processing flow

2. Developer exports to watsonx Orchestrate
3. Creates "Customer Support Agent"
4. Deploys to Slack, Teams, web chat

**End User Experience:**

- Customer asks question in chat
- Agent searches knowledge base (Langflow)
- If needed, creates ticket (Langflow)
- If needed, processes refund (Langflow)
- All automated, instant responses

**Business Value:**

- 80% of questions answered instantly
- 24/7 availability
- Consistent responses
- Reduced support costs

### Use Case 2: IT Helpdesk Automation

**Setup:**

1. Developer builds in Langflow:
   - Password reset flow
   - Software installation flow
   - Access request flow
   - Troubleshooting flow

2. Developer exports to watsonx Orchestrate
3. Creates "IT Helpdesk Agent"
4. Integrates with ServiceNow

**End User Experience:**

- Employee: "I need access to the sales database"
- Agent: Checks permissions (Langflow)
- Agent: Creates ServiceNow ticket (Langflow)
- Agent: Notifies manager for approval
- Agent: Grants access when approved

**Business Value:**

- Instant IT support
- Automated approvals
- Audit trail
- Reduced IT workload

### Use Case 3: Financial Document Processing

**Setup:**

1. Developer builds in Langflow:
   - Invoice extraction flow
   - Expense validation flow
   - SAP posting flow
   - Approval routing flow

2. Developer exports to watsonx Orchestrate
3. Creates "Finance Automation Agent"
4. Connects to SAP

**End User Experience:**

- Employee uploads expense receipt
- Agent extracts data (Langflow)
- Agent validates against policy (Langflow)
- Agent posts to SAP (Langflow)
- Agent notifies employee of status

**Business Value:**

- 90% faster processing
- Reduced errors
- Automatic compliance checks
- Real-time visibility

---

## Technical Flow: What Happens Behind the Scenes

### When Agent Calls a Langflow Tool

```
1. User Request
   ↓
2. watsonx Orchestrate Agent receives request
   ↓
3. Agent decides to use "document_qa" tool
   ↓
4. Agent calls MCP endpoint:
   POST http://localhost:7860/api/v1/mcp/project/{id}/streamable
   {
     "tool": "document_qa",
     "arguments": {
       "file": "document.pdf",
       "question": "What are the key points?"
     }
   }
   ↓
5. Langflow MCP Server receives request
   ↓
6. Langflow executes the "document_qa" flow:
   - Loads PDF
   - Extracts text
   - Sends to LLM
   - Generates answer
   ↓
7. Langflow returns result to watsonx Orchestrate
   {
     "result": "Key points: 1. Revenue up 25%..."
   }
   ↓
8. Agent formats response for user
   ↓
9. User sees answer
```

---

## Deployment Options

### Option 1: Development/Testing

```
Langflow: localhost:7860
watsonx Orchestrate: Cloud
Users: Developers only
```

### Option 2: Production (Cloud)

```
Langflow: https://langflow.company.com
watsonx Orchestrate: IBM Cloud
Users: All employees
```

### Option 3: Production (On-Premise)

```
Langflow: Internal server
watsonx Orchestrate: On-premise
Users: All employees
Security: Behind firewall
```

---

## Maintenance & Updates

### When You Update a Flow in Langflow

1. **Developer updates flow in Langflow UI**
2. **Flow is automatically available** (no re-export needed!)
3. **Agent uses updated version** immediately
4. **No downtime** for users

### When You Add New Flows

1. **Developer creates new flow in Langflow**
2. **Enable MCP for the new flow**
3. **Re-export:** `./scripts/wxo_setup.sh`
4. **Update toolkit:** `./wxo_export/import_toolkit.sh`
5. **Update agent:** Edit agent.yaml to include new tool
6. **Deploy:** `orchestrate agents update -f agent.yaml`

---

## Monitoring & Observability

### What You Can Monitor

**In Langflow:**

- Flow execution times
- Success/failure rates
- Input/output logs
- Error messages

**In watsonx Orchestrate:**

- Agent usage statistics
- Tool call frequency
- User satisfaction
- Response times

**Combined View:**

- End-to-end request tracing
- Performance bottlenecks
- Cost per request
- Usage patterns

---

## Security & Governance

### Access Control

**Langflow Level:**

- Who can create/edit flows
- Who can enable MCP
- API key authentication

**watsonx Orchestrate Level:**

- Who can create agents
- Who can use agents
- Which tools agents can access
- Approval workflows

**Enterprise Level:**

- SSO integration
- Role-based access
- Audit logging
- Compliance reporting

---

## Cost Model

### Development Costs

- Langflow: Open source (free)
- watsonx Orchestrate: IBM licensing
- LLM API calls: Per token pricing

### Operational Costs

- Langflow hosting: Server costs
- watsonx Orchestrate: Per-user licensing
- LLM usage: Based on volume

### ROI Calculation

- Reduced support staff: $X/year
- Faster response times: $Y/year
- Improved customer satisfaction: $Z/year
- **Total ROI:** Typically 300-500% in year 1

---

## Summary: The Complete Journey

1. **Developer builds** AI workflows in Langflow (visual, easy)
2. **Developer exports** to watsonx Orchestrate (one command)
3. **Developer imports** toolkit to watsonx Orchestrate (one command)
4. **Developer creates** agent that uses the tools (one command)
5. **End users interact** with agent via Slack/Teams/web (natural language)
6. **Agent calls** Langflow flows as needed (automatic)
7. **Langflow executes** the AI workflows (fast, reliable)
8. **Users get** instant, accurate answers (great experience)

**Key Insight:** Langflow becomes your **AI workflow engine**, and watsonx Orchestrate becomes your **enterprise deployment platform**. Together, they enable enterprise-grade AI agents that connect to all your systems.
