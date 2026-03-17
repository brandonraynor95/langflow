import { Button } from "@/components/ui/button";
import type {
  DeploymentProvider,
  DeploymentProvidersResponse,
} from "@/controllers/API/queries/deployments/use-deployments";
import StepperModal from "@/modals/stepperModal/StepperModal";
import { StepProvider } from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepProvider";
import { MOCK_PROVIDERS } from "@/pages/MainPage/pages/deploymentsPage/mockData";
import useAlertStore from "@/stores/alertStore";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PROVIDER_OPTIONS } from "../constants";

type RegisterDeploymentProviderModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRegistered?: () => void;
};

export const RegisterDeploymentProviderModal = ({
  open,
  onOpenChange,
  onRegistered,
}: RegisterDeploymentProviderModalProps) => {
  const queryClient = useQueryClient();
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);

  const [providerKey, setProviderKey] = useState("watsonx-orchestrate");
  const [backendUrl, setBackendUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [accountId, setAccountId] = useState("");

  const resetState = () => {
    setProviderKey("watsonx-orchestrate");
    setBackendUrl("");
    setApiKey("");
    setAccountId("");
  };

  const validate = (): string | null => {
    if (!providerKey.trim()) {
      return "Provider key is required.";
    }
    return null;
  };

  const toMockDeploymentProviders = (): DeploymentProvider[] =>
    MOCK_PROVIDERS.map((provider) => ({
      id: provider.id,
      account_id: null,
      provider_key:
        provider.id === "watsonx" ? "watsonx-orchestrate" : provider.id,
      backend_url: provider.endpoint,
      registered_at: new Date().toISOString(),
    }));

  const handleSubmit = () => {
    const validationError = validate();
    if (validationError) {
      setErrorData({ title: validationError });
      return;
    }

    const registeredProvider: DeploymentProvider = {
      id:
        globalThis.crypto?.randomUUID?.() ??
        `mock-provider-${Date.now().toString(36)}`,
      account_id:
        providerKey === "watsonx-orchestrate" ? null : accountId.trim() || null,
      provider_key: providerKey.trim(),
      backend_url: backendUrl.trim() || "https://api.example.com",
      registered_at: new Date().toISOString(),
    };

    const mockProviders = toMockDeploymentProviders();
    const mergedProviders = [registeredProvider, ...mockProviders];

    queryClient.setQueriesData<DeploymentProvidersResponse>(
      { queryKey: ["useGetDeploymentProviders"] },
      (currentData) => ({
        providers: mergedProviders,
        page: currentData?.page ?? 1,
        size: currentData?.size ?? 20,
        total: mergedProviders.length,
      }),
    );

    setSuccessData({
      title: "Deployment provider registered successfully",
    });
    onOpenChange(false);
    onRegistered?.();
    resetState();
  };

  return (
    <StepperModal
      className="p-2"
      open={open}
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen);
        if (!nextOpen) {
          resetState();
        }
      }}
      currentStep={1}
      totalSteps={1}
      showProgress={false}
      title="Provider"
      description=""
      width="w-[752px]"
      height="h-[671px]"
      contentClassName="bg-background"
      closeButtonClassName="top-[20px] right-4"
      footer={
        <div className="flex w-full items-center justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => {
              onOpenChange(false);
              resetState();
            }}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit}>Register Provider</Button>
        </div>
      }
    >
      <StepProvider
        value={{
          selectedProvider: providerKey,
          apiKey,
          serviceUrl: backendUrl,
          accountId,
        }}
        onChange={{
          setSelectedProvider: setProviderKey,
          setApiKey,
          setServiceUrl: setBackendUrl,
          setAccountId,
        }}
        config={{
          providerOptions: PROVIDER_OPTIONS,
          providerLabel: "Choose Provider",
          apiKeyLabel: "API Key",
          apiKeyPlaceholder: "Enter your API key",
          serviceUrlLabel: "Service Instance URL",
          serviceUrlPlaceholder: "https://api.example.com",
          showProviderStatus: true,
          providerGridClassName: "grid-cols-2 gap-4",
          hideFieldsUntilProviderSelected: false,
        }}
      />
    </StepperModal>
  );
};
