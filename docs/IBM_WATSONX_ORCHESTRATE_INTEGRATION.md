# IBM watsonx Orchestrate (Bob) Integration Specification

## Executive Summary

This document outlines the integration strategy between Langflow and IBM watsonx Orchestrate (Bob), positioning Langflow as the visual agent-building layer while Bob acts as the enterprise execution and orchestration layer.

**Vision**: Create the first enterprise-grade visual agent orchestration platform where developers build agent workflows visually in Langflow, and enterprises deploy them securely via Bob with connections to enterprise systems.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Enterprise Users                          │
│        (employees, developers, customers)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Enterprise Interfaces                           │
│   Chat / Slack / Web / Email / Apps / APIs                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         IBM watsonx Orchestrate (Bob)                        │
│      Enterprise Agent Runtime & Skills                       │
│  • Workflow orchestration                                    │
│  • Enterprise connectors (SAP, Salesforce, ServiceNow)      │
│  • Human-in-the-loop                                         │
│  • Governance / audit / RBAC                                 │
│  • Security & authentication                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Langflow                                  │
│          Visual AI Agent Builder                             │
│  • Agent workflow design                                     │
│  • Tool composition                                          │
│  • RAG pipelines                                             │
│  • Reasoning flows                                           │
│  • Multi-model orchestration                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI Models                                  │
│   watsonx.ai / Open Models / LLM APIs                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Enterprise Systems                              │
│   SAP • Salesforce • ServiceNow • Databases                 │
└─────────────────────────────────────────────────────────────┘
```

## Integration Strategy

### Phase 1: MVP - Bob Invokes Langflow (Priority)

**Objective**: Enable Bob users to invoke Langflow flows as enterprise skills.

**Flow**:

1. User builds agent workflow in Langflow
2. Langflow exposes flow as API endpoint
3. Bob registers Langflow endpoint as a skill
4. Bob users invoke the skill through Bob interface
5. Bob handles authentication, governance, and audit

**Key Components**:

- Langflow API endpoints for flow execution
- Bob skill registration mechanism
- Authentication/authorization bridge
- Execution monitoring and logging

### Phase 2: Future - Langflow Uses Bob Skills

**Objective**: Enable Langflow users to use Bob enterprise connectors as components.

**Note**: Currently blocked as Bob team doesn't expose APIs. This will be revisited when Bob provides API access.

## Technical Implementation

### 1. Langflow Export Format for Bob

Langflow flows will be exportable in a Bob-compatible format:

```json
{
  "agent_id": "customer_support_agent",
  "name": "Customer Support Agent",
  "description": "Handles customer inquiries with RAG and enterprise tools",
  "version": "1.0.0",
  "langflow_flow_id": "uuid-here",
  "tools": [
    {
      "name": "salesforce_lookup",
      "type": "enterprise_connector",
      "provider": "bob"
    },
    {
      "name": "servicenow_ticket",
      "type": "enterprise_connector",
      "provider": "bob"
    },
    {
      "name": "rag_knowledgebase",
      "type": "langflow_component",
      "provider": "langflow"
    }
  ],
  "inputs": [
    {
      "name": "user_query",
      "type": "string",
      "required": true
    }
  ],
  "outputs": [
    {
      "name": "response",
      "type": "string"
    }
  ],
  "execution_endpoint": "https://langflow.company.com/api/v1/run/{flow_id}",
  "authentication": {
    "type": "api_key",
    "header": "x-api-key"
  },
  "governance": {
    "requires_approval": false,
    "audit_level": "full",
    "rbac_roles": ["customer_support", "admin"]
  }
}
```

### 2. API Endpoints

#### New Langflow API Endpoints

```python
# src/backend/base/langflow/api/v1/bob_integration.py

@router.post("/bob/export/{flow_id}")
async def export_flow_for_bob(
    flow_id: UUID,
    session: DbSession,
    current_user: CurrentActiveUser,
) -> BobSkillExportResponse:
    """Export a Langflow flow in Bob-compatible format."""
    pass

@router.post("/bob/register/{flow_id}")
async def register_flow_with_bob(
    flow_id: UUID,
    bob_config: BobRegistrationConfig,
    session: DbSession,
    current_user: CurrentActiveUser,
) -> BobRegistrationResponse:
    """Register a Langflow flow as a Bob skill."""
    pass

@router.get("/bob/status/{flow_id}")
async def get_bob_deployment_status(
    flow_id: UUID,
    session: DbSessionReadOnly,
    current_user: CurrentActiveUser,
) -> BobDeploymentStatus:
    """Get the Bob deployment status for a flow."""
    pass

@router.post("/bob/execute")
async def execute_flow_from_bob(
    execution_request: BobExecutionRequest,
    session: DbSession,
) -> BobExecutionResponse:
    """Execute a Langflow flow invoked by Bob."""
    pass
```

### 3. Database Schema Extensions

```python
# New table: bob_deployments
class BobDeployment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    flow_id: UUID = Field(foreign_key="flow.id")
    bob_skill_id: str  # Bob's internal skill identifier
    bob_endpoint: str  # Bob API endpoint
    status: str  # active, inactive, error
    created_at: datetime
    updated_at: datetime
    user_id: UUID = Field(foreign_key="user.id")

    # Configuration
    authentication_config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    governance_config: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Metadata
    deployment_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
```

### 4. Bob Service Layer

```python
# src/backend/base/langflow/services/bob/service.py

class BobIntegrationService:
    """Service for managing Bob integration."""

    async def export_flow_to_bob_format(
        self,
        flow: Flow
    ) -> BobSkillDefinition:
        """Convert Langflow flow to Bob skill format."""
        pass

    async def register_skill_with_bob(
        self,
        flow: Flow,
        bob_config: BobConfig
    ) -> BobRegistrationResult:
        """Register flow as Bob skill via Bob API."""
        pass

    async def validate_bob_credentials(
        self,
        credentials: BobCredentials
    ) -> bool:
        """Validate Bob API credentials."""
        pass

    async def sync_deployment_status(
        self,
        deployment_id: UUID
    ) -> BobDeploymentStatus:
        """Sync deployment status with Bob."""
        pass
```

### 5. Frontend Components

#### Bob Deployment Modal

```typescript
// src/frontend/src/modals/BobDeploymentModal/index.tsx

interface BobDeploymentModalProps {
  flowId: string;
  flowName: string;
  onClose: () => void;
}

export function BobDeploymentModal({
  flowId,
  flowName,
  onClose,
}: BobDeploymentModalProps) {
  // UI for:
  // 1. Bob credentials configuration
  // 2. Skill name and description
  // 3. Governance settings (RBAC, audit level)
  // 4. Deployment preview
  // 5. Deploy button
  // 6. Status monitoring
}
```

#### Bob Deployment Button

```typescript
// Add to flow toolbar
<Button
  onClick={() => setShowBobDeployModal(true)}
  icon={<BobIcon />}
>
  Deploy to watsonx Orchestrate
</Button>
```

## Use Cases

### 1. Enterprise Copilot

**Scenario**: Employee asks "Why is order 456 delayed?"

**Flow**:

```
User Question (Bob Interface)
    ↓
Bob invokes Langflow skill
    ↓
Langflow Agent:
  - RAG over internal docs
  - Query SAP (via Bob connector)
  - Check logistics system
  - Generate explanation
    ↓
Response to Bob
    ↓
Bob displays to user (with audit trail)
```

### 2. IT Automation

**Scenario**: Employee requests software installation

**Flow**:

```
Employee Request (Bob)
    ↓
Langflow Agent validates request
    ↓
Bob creates ServiceNow ticket
    ↓
Langflow monitors status
    ↓
Bob notifies employee
```

### 3. HR Assistant

**Scenario**: Employee asks about vacation policy

**Flow**:

```
Question (Bob)
    ↓
Langflow RAG over HR docs
    ↓
If approved: Bob submits leave request
    ↓
Confirmation to employee
```

## Security & Governance

### Authentication Flow

```
Bob User Request
    ↓
Bob validates user (RBAC)
    ↓
Bob calls Langflow with service account token
    ↓
Langflow validates token
    ↓
Langflow executes flow
    ↓
Langflow returns result
    ↓
Bob logs execution (audit trail)
    ↓
Bob returns to user
```

### Key Security Features

1. **API Key Management**: Secure storage of Bob credentials in Langflow
2. **Service Account**: Dedicated service account for Bob-to-Langflow communication
3. **Audit Logging**: Full execution traces for compliance
4. **RBAC Integration**: Respect Bob's role-based access control
5. **Data Encryption**: TLS for all communications

## Deployment Models

### Option A: Langflow OSS + Bob SaaS

- Best for experimentation and small teams
- Quick setup
- Limited enterprise features

### Option B: Langflow Enterprise + watsonx Orchestrate (Strategic)

- Full IBM AI stack integration
- On-premises deployment
- Complete governance and compliance
- Enterprise support

## Competitive Advantages

| Platform                 | Limitation                    | Langflow + Bob Advantage                      |
| ------------------------ | ----------------------------- | --------------------------------------------- |
| OpenAI Agent Tools       | Weak enterprise orchestration | Full enterprise governance + visual builder   |
| Microsoft Copilot Studio | Limited visual flexibility    | Complete workflow control + open ecosystem    |
| Salesforce Agentforce    | CRM-only                      | Any enterprise system (SAP, ServiceNow, etc.) |

## Implementation Roadmap

### Phase 1: MVP (3 months)

- [ ] Bob skill export format
- [ ] API endpoints for Bob invocation
- [ ] Basic authentication bridge
- [ ] Frontend deployment UI
- [ ] Documentation and examples

### Phase 2: Enterprise Features (6 months)

- [ ] Agent registry
- [ ] Advanced monitoring and observability
- [ ] Version management
- [ ] Multi-agent orchestration
- [ ] Enhanced governance controls

### Phase 3: Autonomous Agents (12 months)

- [ ] Planning agents
- [ ] Agent collaboration
- [ ] Human oversight loops
- [ ] Advanced reasoning capabilities

## Success Metrics

1. **Adoption**: Number of flows deployed to Bob
2. **Usage**: Execution volume through Bob
3. **Enterprise Accounts**: Number of enterprise customers using integration
4. **Time to Value**: Time from flow creation to Bob deployment
5. **Reliability**: Uptime and error rates

## Documentation Requirements

1. **Setup Guide**: How to configure Bob integration
2. **Developer Guide**: Building Bob-compatible flows
3. **API Reference**: Complete API documentation
4. **Security Guide**: Authentication and authorization setup
5. **Use Case Examples**: Sample flows for common scenarios
6. **Troubleshooting**: Common issues and solutions

## Open Questions

1. **Bob API Access**: When will Bob expose APIs for Langflow to consume Bob skills?
2. **Authentication Standards**: What authentication methods does Bob support?
3. **Rate Limiting**: What are Bob's rate limits for skill invocations?
4. **Monitoring Integration**: Can we integrate with Bob's monitoring systems?
5. **Billing**: How will usage be tracked and billed?

## Next Steps

1. Schedule technical alignment meeting with Bob team
2. Define API contracts between Langflow and Bob
3. Create proof-of-concept implementation
4. Develop integration test suite
5. Create customer-facing documentation
6. Plan beta program with select customers

## References

- [Langflow Documentation](https://docs.langflow.org)
- [IBM watsonx Orchestrate Documentation](https://www.ibm.com/products/watsonx-orchestrate)
- [Integration Demo Video](https://www.youtube.com/watch?v=5v8E-YbSPMo)

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-13  
**Owner**: Langflow Engineering Team  
**Status**: Draft - Pending Review
