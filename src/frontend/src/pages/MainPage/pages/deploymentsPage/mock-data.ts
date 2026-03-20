import type {
  ConnectionItem,
  FlowWithVersions,
} from "./components/StepAttachFlows";
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

export const MOCK_FLOWS_WITH_VERSIONS: FlowWithVersions[] = [
  {
    id: "flow-1",
    name: "Qualify Lead",
    icon: "Workflow",
    versions: [
      { id: "v1-3", label: "v3", lastUpdated: "2026-02-18" },
      { id: "v1-2", label: "v2", lastUpdated: "2026-02-15" },
      { id: "v1-1", label: "v1", lastUpdated: "2026-02-10" },
    ],
  },
  {
    id: "flow-2",
    name: "Summarize Call Notes",
    icon: "Workflow",
    versions: [
      { id: "v2-2", label: "v2", lastUpdated: "2026-02-14" },
      { id: "v2-1", label: "v1", lastUpdated: "2026-02-08" },
    ],
  },
  {
    id: "flow-3",
    name: "Create Ticket",
    icon: "Workflow",
    versions: [
      { id: "v3-4", label: "v4", lastUpdated: "2026-02-17" },
      { id: "v3-3", label: "v3", lastUpdated: "2026-02-13" },
      { id: "v3-2", label: "v2", lastUpdated: "2026-02-09" },
      { id: "v3-1", label: "v1", lastUpdated: "2026-02-05" },
    ],
  },
  {
    id: "flow-4",
    name: "Email Response Bot",
    icon: "Workflow",
    versions: [{ id: "v4-1", label: "v1", lastUpdated: "2026-02-12" }],
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
