import { Button } from "@/components/ui/button";
import { usePostCreateDeploymentProvider } from "@/controllers/API/queries/deployments/use-deployments";
import StepperModal from "@/modals/stepperModal/StepperModal";
import { StepProvider } from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepProvider";
import useAlertStore from "@/stores/alertStore";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PROVIDER_OPTIONS } from "../constants";

type RegisterDeploymentProviderModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export const RegisterDeploymentProviderModal = ({
  open,
  onOpenChange,
}: RegisterDeploymentProviderModalProps) => {
  const queryClient = useQueryClient();
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const { mutate: createProvider, isPending } =
    usePostCreateDeploymentProvider();

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
    if (!backendUrl.trim()) {
      return "Backend URL is required.";
    }
    if (!apiKey.trim()) {
      return "API key is required.";
    }
    return null;
  };

  const handleSubmit = () => {
    const validationError = validate();
    if (validationError) {
      setErrorData({ title: validationError });
      return;
    }

    createProvider(
      {
        provider_key: providerKey.trim(),
        backend_url: backendUrl.trim(),
        api_key: apiKey.trim(),
        account_id:
          providerKey === "watsonx-orchestrate"
            ? undefined
            : accountId.trim() || undefined,
      },
      {
        onSuccess: async () => {
          await queryClient.invalidateQueries({
            queryKey: ["useGetDeploymentProviders"],
          });
          setSuccessData({
            title: "Deployment provider registered successfully",
          });
          onOpenChange(false);
          resetState();
        },
        onError: () => {
          setErrorData({
            title: "Could not register deployment provider",
            list: ["Check your backend URL/API key and try again."],
          });
        },
      },
    );
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
          <Button onClick={handleSubmit} loading={isPending}>
            Register Provider
          </Button>
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
