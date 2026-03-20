export type DeploymentProviderType = "watsonx" | "kubernetes";

export interface DeploymentProvider {
  id: string;
  type: DeploymentProviderType;
  name: string;
  icon: string;
  connected: boolean;
}

export interface ProviderInstance {
  id: string;
  name: string;
  lastUsed: string;
}

export interface ProviderCredentials {
  apiKey: string;
  serviceUrl: string;
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
