import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import LangflowLogoColor from "@/assets/LangflowLogoColor.svg?react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { usePostCreateDeploymentProvider } from "@/controllers/API/queries/deployments/use-deployments";
import IBMSvg from "@/icons/IBM/ibm/IBM";
import {
  StepProvider,
  type StepProviderOption,
} from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepProvider";
import useAlertStore from "@/stores/alertStore";

type RegisterDeploymentProviderModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const PROVIDER_OPTIONS: StepProviderOption[] = [
  {
    key: "watsonx-orchestrate",
    label: "Watsonx",
    tool: "Orchestrate",
    serviceUrlPlaceholder:
      "https://api.<region>.watson-orchestrate.ibm.com/instances/<id>",
    iconNode: (
      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-white">
        <IBMSvg className="h-5 w-5 text-[#0F62FE]" />
      </div>
    ),
  },
  {
    key: "langflow",
    label: "Langflow",
    tool: "Deployments",
    serviceUrlPlaceholder: "https://langflow.example.com",
    iconNode: <LangflowLogoColor className="h-8 w-8" />,
    requiresAccountId: true,
  },
];

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
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen);
        if (!nextOpen) {
          resetState();
        }
      }}
    >
      <DialogContent
        className="flex max-h-[85vh] h-[580px] max-w-[752px] flex-col gap-0 overflow-visible border bg-background p-0 shadow-lg"
        closeButtonClassName="top-4 right-4"
      >
        <div className="flex flex-col gap-1 px-4 pt-4 pr-14">
          <DialogTitle className="text-base font-semibold">
            Configure Deployment Provider
          </DialogTitle>
          <DialogDescription>
            Configure your provider credentials below. Sign in or sign up to
            find your credentials
          </DialogDescription>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto rounded-lg px-4 py-4">
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
        </div>

        <div className="flex items-center px-4 pb-4">
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
        </div>
      </DialogContent>
    </Dialog>
  );
};
