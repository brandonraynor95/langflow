import type { ConnectionItem } from "./components/StepAttachFlows";
import type { Deployment, DeploymentProvider, ProviderInstance } from "./types";

export const MOCK_PROVIDERS: DeploymentProvider[] = [
  {
    id: "watsonx",
    type: "watsonx",
    name: "watsonx Orchestrate",
    icon: "Bot",
    connected: true,
  },
  {
    id: "kubernetes",
    type: "kubernetes",
    name: "Kubernetes",
    icon: "Container",
    connected: true,
  },
];

export const MOCK_PROVIDER_INSTANCES: ProviderInstance[] = [
  {
    id: "inst-1",
    name: "Production Instance",
    lastUsed: "Last used 2 hours ago",
  },
  {
    id: "inst-2",
    name: "Staging Instance",
    lastUsed: "Last used 1 day ago",
  },
  {
    id: "inst-3",
    name: "Development Instance",
    lastUsed: "Last used 3 days ago",
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
