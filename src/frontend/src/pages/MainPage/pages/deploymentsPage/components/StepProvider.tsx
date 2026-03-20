import { useState } from "react";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Input } from "@/components/ui/input";
import { cn } from "@/utils/utils";
import { useDeploymentStepper } from "../contexts/DeploymentStepperContext";
import { MOCK_PROVIDER_INSTANCES, MOCK_PROVIDERS } from "../mock-data";
import type {
  DeploymentProvider,
  ProviderCredentials,
  ProviderInstance,
} from "../types";

type InstanceTab = "existing" | "new";

function ProviderCard({
  provider,
  selected,
  onSelect,
}: {
  provider: DeploymentProvider;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex h-[80px] items-center gap-3 rounded-lg border bg-muted p-3 text-left transition-colors",
        selected
          ? "border-2 border-foreground"
          : "border-border hover:border-muted-foreground",
      )}
    >
      <ForwardedIconComponent
        name={provider.icon}
        className={cn(
          "h-8 w-8",
          selected ? "text-foreground" : "text-muted-foreground",
        )}
      />
      <div className="flex flex-col text-left">
        <span className="pb-1 text-sm font-medium">{provider.name}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span
            className={cn(
              "inline-block h-1.5 w-1.5 rounded-full",
              provider.connected
                ? "bg-accent-emerald-foreground"
                : "bg-muted-foreground",
            )}
          />
          {provider.connected ? "Connected" : "Not Connected"}
        </span>
      </div>
    </button>
  );
}

function InstanceTabToggle({
  activeTab,
  onTabChange,
}: {
  activeTab: InstanceTab;
  onTabChange: (tab: InstanceTab) => void;
}) {
  return (
    <div className="rounded-xl border border-border bg-muted p-1">
      <div className="grid grid-cols-2 gap-4">
        {(["existing", "new"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={cn(
              "rounded-lg py-2 text-sm transition-colors",
              activeTab === tab
                ? "bg-background"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab === "existing"
              ? "Choose existing instance"
              : "Add new instance"}
          </button>
        ))}
      </div>
    </div>
  );
}

function InstanceList({
  instances,
  selectedInstance,
  onSelectInstance,
}: {
  instances: ProviderInstance[];
  selectedInstance: ProviderInstance | null;
  onSelectInstance: (instance: ProviderInstance) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-sm text-muted-foreground">
        Select from your existing instances
      </span>
      {instances.map((instance) => {
        const isSelected = selectedInstance?.id === instance.id;
        return (
          <button
            key={instance.id}
            type="button"
            onClick={() => onSelectInstance(instance)}
            className={cn(
              "flex items-center gap-4 rounded-xl border bg-muted p-3 text-left transition-colors",
              isSelected
                ? "border-primary"
                : "border-transparent hover:border-border",
            )}
          >
            <span
              className={cn(
                "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded",
                isSelected
                  ? "bg-primary text-primary-foreground"
                  : "border border-muted-foreground bg-background",
              )}
            >
              {isSelected && (
                <ForwardedIconComponent name="Check" className="h-3.5 w-3.5" />
              )}
            </span>
            <span className="flex flex-col">
              <span className="text-sm font-medium leading-tight">
                {instance.name}
              </span>
              <span className="text-sm leading-tight text-muted-foreground">
                {instance.lastUsed}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function NewInstanceForm({
  provider,
  credentials,
  onCredentialsChange,
}: {
  provider: DeploymentProvider;
  credentials: ProviderCredentials;
  onCredentialsChange: (credentials: ProviderCredentials) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Configure your {provider.name} credentials below. Sign in or sign up to{" "}
        <span className="font-semibold text-foreground">
          find your credentials
        </span>
        .
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col">
          <span className="pb-2 text-sm font-medium">
            API Key <span className="text-destructive">*</span>
          </span>
          <Input
            type="password"
            placeholder="Enter your API key"
            className="bg-muted"
            value={credentials.apiKey}
            onChange={(e) =>
              onCredentialsChange({
                ...credentials,
                apiKey: e.target.value,
              })
            }
          />
        </div>
        <div className="flex flex-col">
          <span className="pb-2 text-sm font-medium">
            Service Instance URL <span className="text-destructive">*</span>
          </span>
          <Input
            type="url"
            placeholder="https://api.example.com"
            className="bg-muted"
            value={credentials.serviceUrl}
            onChange={(e) =>
              onCredentialsChange({
                ...credentials,
                serviceUrl: e.target.value,
              })
            }
          />
        </div>
      </div>
    </div>
  );
}

export default function StepProvider() {
  const {
    selectedProvider,
    setSelectedProvider,
    selectedInstance,
    setSelectedInstance,
    credentials,
    setCredentials,
  } = useDeploymentStepper();
  const providers = MOCK_PROVIDERS;
  const instances = MOCK_PROVIDER_INSTANCES;
  const hasInstances = instances.length > 0;

  const [instanceTab, setInstanceTab] = useState<InstanceTab>(
    hasInstances ? "existing" : "new",
  );

  return (
    <div className="flex h-full w-full flex-col gap-6 overflow-y-auto py-3">
      <h2 className="text-lg font-semibold">Provider</h2>

      <div className="flex flex-col gap-3">
        <span className="pb-2 text-sm font-medium">
          Choose Provider <span className="text-destructive">*</span>
        </span>
        <div className="grid grid-cols-2 gap-4">
          {providers.map((provider) => (
            <ProviderCard
              key={provider.id}
              provider={provider}
              selected={selectedProvider?.id === provider.id}
              onSelect={() => setSelectedProvider(provider)}
            />
          ))}
        </div>
      </div>

      {selectedProvider && (
        <>
          {hasInstances ? (
            <div className="flex flex-col gap-4">
              <InstanceTabToggle
                activeTab={instanceTab}
                onTabChange={setInstanceTab}
              />
              {instanceTab === "existing" ? (
                <InstanceList
                  instances={instances}
                  selectedInstance={selectedInstance}
                  onSelectInstance={setSelectedInstance}
                />
              ) : (
                <NewInstanceForm
                  provider={selectedProvider}
                  credentials={credentials}
                  onCredentialsChange={setCredentials}
                />
              )}
            </div>
          ) : (
            <NewInstanceForm
              provider={selectedProvider}
              credentials={credentials}
              onCredentialsChange={setCredentials}
            />
          )}
        </>
      )}
    </div>
  );
}
