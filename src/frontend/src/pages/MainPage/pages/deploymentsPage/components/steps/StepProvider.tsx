import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Input } from "@/components/ui/input";
import type { ReactNode } from "react";
import { useState } from "react";

export type StepProviderOption = {
  key: string;
  label: string;
  icon?: string;
  iconNode?: ReactNode;
  requiresAccountId?: boolean;
  serviceUrlPlaceholder?: string;
};

const DEFAULT_PROVIDERS: StepProviderOption[] = [
  {
    key: "watsonx",
    label: "Watsonx",
    icon: "WatsonxOrchestrate",
  },
  { key: "aws", label: "AWS", icon: "AWS" },
  { key: "azure", label: "Azure", icon: "Azure" },
  { key: "gcp", label: "Google", icon: "Google" },
];

export type StepProviderValue = {
  selectedProvider?: string;
  apiKey: string;
  serviceUrl: string;
  accountId?: string;
};

export type StepProviderChangeHandlers = {
  setSelectedProvider?: (value: string) => void;
  setApiKey: (value: string) => void;
  setServiceUrl: (value: string) => void;
  setAccountId?: (value: string) => void;
};

export type StepProviderConfig = {
  providerOptions?: StepProviderOption[];
  providerLabel?: string;
  apiKeyLabel?: string;
  apiKeyPlaceholder?: string;
  serviceUrlLabel?: string;
  serviceUrlPlaceholder?: string;
  showProviderStatus?: boolean;
  providerGridClassName?: string;
  hideFieldsUntilProviderSelected?: boolean;
  accountIdLabel?: string;
  accountIdPlaceholder?: string;
};

const DEFAULT_CONFIG: Required<StepProviderConfig> = {
  providerOptions: DEFAULT_PROVIDERS,
  providerLabel: "Choose Provider",
  apiKeyLabel: "API Key",
  apiKeyPlaceholder: "Enter your API key",
  serviceUrlLabel: "Service Instance URL",
  serviceUrlPlaceholder: "https://api.example.com",
  showProviderStatus: true,
  providerGridClassName: "grid-cols-4 gap-3",
  hideFieldsUntilProviderSelected: false,
  accountIdLabel: "Account ID (optional)",
  accountIdPlaceholder: "Provider account/tenant id",
};

type ResolvedStepProviderConfig = Required<StepProviderConfig>;

const PROVIDER_CARD_BASE_CLASS =
  "rounded-lg border p-3 bg-muted transition-colors h-[80px]";
const PROVIDER_CARD_SELECTED_CLASS = "border-2 border-foreground";
const PROVIDER_CARD_UNSELECTED_CLASS =
  "border-border hover:border-muted-foreground";
const PROVIDER_ICON_SIZE_CLASS = "h-8 w-8";
const PROVIDER_ICON_SELECTED_CLASS = "text-foreground";
const PROVIDER_ICON_UNSELECTED_CLASS = "text-muted-foreground";

type ExistingInstanceOption = {
  id: string;
  name: string;
  lastUsed: string;
};

const EXISTING_INSTANCE_OPTIONS: ExistingInstanceOption[] = [
  {
    id: "production",
    name: "Production Instance",
    lastUsed: "Last used 2 hours ago",
  },
  { id: "staging", name: "Staging Instance", lastUsed: "Last used 1 day ago" },
  {
    id: "development",
    name: "Development Instance",
    lastUsed: "Last used 3 days ago",
  },
];

const resolveConfig = (
  config?: StepProviderConfig,
): ResolvedStepProviderConfig => ({
  ...DEFAULT_CONFIG,
  ...config,
  providerOptions: config?.providerOptions ?? DEFAULT_CONFIG.providerOptions,
});

const getSelectedProvider = (
  controlledProvider: string | undefined,
  internalProvider: string,
  providerOptions: StepProviderOption[],
): string =>
  controlledProvider || internalProvider || providerOptions[0]?.key || "";

const getActiveProvider = (
  providerOptions: StepProviderOption[],
  selectedProvider: string,
): StepProviderOption | undefined =>
  providerOptions.find((provider) => provider.key === selectedProvider) ??
  providerOptions[0];

type StepProviderProps = {
  value: StepProviderValue;
  onChange: StepProviderChangeHandlers;
  config?: StepProviderConfig;
};

export const StepProvider = ({
  value,
  onChange,
  config,
}: StepProviderProps) => {
  const [instanceMode, setInstanceMode] = useState<"existing" | "new">(
    "existing",
  );
  const [selectedExistingInstanceId, setSelectedExistingInstanceId] =
    useState<string>("production");
  const resolvedConfig = resolveConfig(config);
  const {
    providerOptions,
    providerLabel,
    apiKeyLabel,
    apiKeyPlaceholder,
    serviceUrlLabel,
    serviceUrlPlaceholder,
    showProviderStatus,
    providerGridClassName,
    hideFieldsUntilProviderSelected,
    accountIdLabel,
    accountIdPlaceholder,
  } = resolvedConfig;

  const [internalSelectedProvider, setInternalSelectedProvider] =
    useState<string>(providerOptions[0]?.key ?? "");

  const selectedProvider = getSelectedProvider(
    value.selectedProvider,
    internalSelectedProvider,
    providerOptions,
  );

  const setSelectedProvider = (nextSelectedProvider: string) => {
    if (onChange.setSelectedProvider) {
      onChange.setSelectedProvider(nextSelectedProvider);
      return;
    }
    setInternalSelectedProvider(nextSelectedProvider);
  };

  const activeProvider = getActiveProvider(providerOptions, selectedProvider);

  const showCredentialsSection =
    !hideFieldsUntilProviderSelected || Boolean(selectedProvider);

  return (
    <div className="flex h-full w-full flex-col gap-6 overflow-y-auto py-3">
      <div className="flex flex-col">
        <span className="text-sm font-medium pb-2">
          {providerLabel} <span className="text-destructive">*</span>
        </span>
        <div className={`grid ${providerGridClassName}`}>
          {providerOptions.map((provider) => {
            const isSelected = selectedProvider === provider.key;
            return (
              <button
                key={provider.key}
                type="button"
                onClick={() => setSelectedProvider(provider.key)}
                className={`${PROVIDER_CARD_BASE_CLASS} ${isSelected
                    ? PROVIDER_CARD_SELECTED_CLASS
                    : PROVIDER_CARD_UNSELECTED_CLASS
                  }`}
              >
                <div className="flex flex-col">
                  <div className="flex flex-row gap-3 justify-start items-center">
                    {provider.iconNode ? (
                      provider.iconNode
                    ) : (
                      <ForwardedIconComponent
                        name={provider.icon ?? "Cloud"}
                        className={`${PROVIDER_ICON_SIZE_CLASS} ${isSelected
                            ? PROVIDER_ICON_SELECTED_CLASS
                            : PROVIDER_ICON_UNSELECTED_CLASS
                          }`}
                      />
                    )}
                    <div className="flex flex-col text-left">
                      <span className="text-sm font-medium pb-1">
                        {provider.label}
                      </span>
                      {showProviderStatus && (
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <span className="inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                          Not connected
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border border-border p-2 bg-muted">
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => setInstanceMode("existing")}
            className={`rounded-lg text-sm py-2 transition-colors ${instanceMode === "existing"
                ? "bg-background"
                : "text-muted-foreground hover:text-foreground"
              }`}
          >
            Choose existing instance
          </button>
          <button
            type="button"
            onClick={() => setInstanceMode("new")}
            className={`rounded-lg text-sm  transition-colors ${instanceMode === "new"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
              }`}
          >
            Add new instance
          </button>
        </div>
      </div>

      {instanceMode === "existing" ? (
        <div className="flex flex-col gap-3">
          <span className="text-sm text-muted-foreground">
            Select from your existing instances
          </span>
          {EXISTING_INSTANCE_OPTIONS.map((instance) => {
            const isSelected = selectedExistingInstanceId === instance.id;
            return (
              <button
                key={instance.id}
                type="button"
                onClick={() => setSelectedExistingInstanceId(instance.id)}
                className={`flex items-center gap-4 rounded-xl border p-4 text-left transition-colors ${isSelected
                    ? "border-foreground bg-muted"
                    : "border-border bg-muted hover:border-muted-foreground"
                  }`}
              >
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-md border ${isSelected
                      ? "border-foreground bg-background"
                      : "border-muted-foreground bg-background"
                    }`}
                >
                  {isSelected && (
                    <ForwardedIconComponent name="Check" className="h-4 w-4" />
                  )}
                </span>
                <span className="flex flex-col">
                  <span className="text-sm font-medium leading-tight">
                    {instance.name}
                  </span>
                  <span className="text-sm text-muted-foreground leading-tight">
                    {instance.lastUsed}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        showCredentialsSection && (
          <div className="grid grid-cols-1 gap-4">
            <div className="flex flex-1 flex-col">
              <span className="text-sm font-medium pb-2">
                {apiKeyLabel} <span className="text-destructive">*</span>
              </span>
              <Input
                type="password"
                placeholder={apiKeyPlaceholder}
                className="bg-muted"
                value={value.apiKey}
                onChange={(e) => onChange.setApiKey(e.target.value)}
              />
            </div>

            <div className="flex flex-1 flex-col">
              <span className="text-sm font-medium pb-2">
                {serviceUrlLabel} <span className="text-destructive">*</span>
              </span>
              <Input
                placeholder={
                  activeProvider?.serviceUrlPlaceholder ?? serviceUrlPlaceholder
                }
                value={value.serviceUrl}
                className="bg-muted"
                onChange={(e) => onChange.setServiceUrl(e.target.value)}
              />
            </div>

            {activeProvider?.requiresAccountId && onChange.setAccountId && (
              <div className="flex flex-col">
                <span className="text-sm font-medium pb-2">
                  {accountIdLabel}
                </span>
                <Input
                  placeholder={accountIdPlaceholder}
                  value={value.accountId ?? ""}
                  className="bg-muted"
                  onChange={(e) => onChange.setAccountId?.(e.target.value)}
                />
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
};
