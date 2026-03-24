import type { ConnectionItem } from "./components/step-attach-flows";
import type { Deployment, DeploymentProvider, ProviderAccount } from "./types";

export const MOCK_PROVIDERS: DeploymentProvider[] = [
  {
    id: "watsonx",
    type: "watsonx",
    name: "watsonx Orchestrate",
    icon: "Bot",
    connected: true,
  },
];

export const MOCK_PROVIDER_INSTANCES: ProviderAccount[] = [
  {
    id: "550e8400-e29b-41d4-a716-446655440001",
    provider_tenant_id: "tenant-prod",
    provider_key: "watsonx_orchestrate",
    provider_url: "https://api.us-south.assistant.watson.cloud.ibm.com/prod",
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-03-22T14:30:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440002",
    provider_tenant_id: "tenant-staging",
    provider_key: "watsonx_orchestrate",
    provider_url: "https://api.us-south.assistant.watson.cloud.ibm.com/staging",
    created_at: "2026-01-20T09:00:00Z",
    updated_at: "2026-03-21T11:00:00Z",
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440003",
    provider_tenant_id: null,
    provider_key: "watsonx_orchestrate",
    provider_url:
      "https://api.us-south.assistant.watson.cloud.ibm.com/development",
    created_at: "2026-02-01T08:00:00Z",
    updated_at: "2026-03-20T16:45:00Z",
  },
];

export const MOCK_CONNECTIONS: ConnectionItem[] = [
  { id: "conn-1", name: "Production Connection A", variableCount: 12 },
  { id: "conn-2", name: "Production Connection B", variableCount: 8 },
  { id: "conn-3", name: "Staging Connection A", variableCount: 10 },
  { id: "conn-4", name: "Development Connection", variableCount: 6 },
];

export const MOCK_DEPLOYMENTS: Deployment[] = [
  {
    id: "1",
    name: "Staging Environment",
    url: "https://api.dev.example.com",
    type: "agent",
    status: "draft",
    health: "pending",
    attachedCount: 2,
    provider: "Langflow Cloud",
    lastModified: "2026-02-10",
    lastModifiedBy: "Sarah Han",
  },
  {
    id: "2",
    name: "Production Main Deployment",
    url: "https://api.production.example.com",
    type: "agent",
    status: "production",
    health: "healthy",
    attachedCount: 1,
    provider: "Langflow Cloud",
    lastModified: "2026-02-09",
    lastModifiedBy: "Sarah Han",
  },
  {
    id: "3",
    name: "Test Environment A",
    url: "https://api.staging.example.com",
    type: "agent",
    status: "draft",
    health: "healthy",
    attachedCount: 1,
    provider: "watsonx Orchestrate",
    lastModified: "2026-02-08",
    lastModifiedBy: "Sarah Han",
  },
  {
    id: "4",
    name: "Development Instance",
    url: "https://api.dev.example.com",
    type: "mcp",
    status: "draft",
    health: "unhealthy",
    attachedCount: 2,
    provider: "AWS Cloud Deploy",
    lastModified: "2026-02-06",
    lastModifiedBy: "Sarah Han",
  },
];
