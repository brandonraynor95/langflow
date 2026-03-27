export type DeploymentProviderType = "watsonx" | "kubernetes";

export interface ConnectionItem {
  id: string;
  name: string;
  variableCount: number;
}

export interface DeploymentProvider {
  id: string;
  type: DeploymentProviderType;
  name: string;
  icon: string;
  connected: boolean;
}

export interface ProviderAccount {
  id: string;
  name: string;
  provider_tenant_id: string | null;
  provider_key: string;
  provider_url: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProviderCredentials {
  name: string;
  provider_key: string;
  provider_url: string;
  api_key: string;
}

export type DeploymentType = "agent" | "mcp";

export type DeploymentStatus = "draft" | "production";

export type DeploymentHealth = "healthy" | "unhealthy" | "pending";

export interface Deployment {
  id: string;
  name: string;
  url: string;
  type: DeploymentType;
  status: DeploymentStatus;
  health: DeploymentHealth;
  attachedCount: number;
  provider: string;
  lastModified: string;
  lastModifiedBy: string;
}
