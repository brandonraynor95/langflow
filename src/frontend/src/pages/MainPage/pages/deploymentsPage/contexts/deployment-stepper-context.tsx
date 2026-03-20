import {
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import type {
  DeploymentProvider,
  DeploymentType,
  ProviderCredentials,
  ProviderInstance,
} from "../types";

interface DeploymentStepperContextType {
  // Navigation
  currentStep: number;
  canGoNext: boolean;
  handleNext: () => void;
  handleBack: () => void;

  // Step 1: Provider
  selectedProvider: DeploymentProvider | null;
  setSelectedProvider: (provider: DeploymentProvider) => void;
  selectedInstance: ProviderInstance | null;
  setSelectedInstance: (instance: ProviderInstance | null) => void;
  credentials: ProviderCredentials;
  setCredentials: (credentials: ProviderCredentials) => void;

  // Step 2: Type
  deploymentType: DeploymentType;
  setDeploymentType: (type: DeploymentType) => void;
  deploymentName: string;
  setDeploymentName: (name: string) => void;
  deploymentDescription: string;
  setDeploymentDescription: (description: string) => void;

  // Step 3: Attach Flows
  selectedVersionByFlow: Map<string, { versionId: string; versionTag: string }>;
  handleSelectVersion: (
    flowId: string,
    versionId: string,
    versionTag: string,
  ) => void;
  attachedConnectionByFlow: Map<string, string>;
  setAttachedConnectionByFlow: Dispatch<SetStateAction<Map<string, string>>>;
}

const DeploymentStepperContext =
  createContext<DeploymentStepperContextType | null>(null);

export function DeploymentStepperProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedProvider, setSelectedProviderState] =
    useState<DeploymentProvider | null>(null);
  const [selectedInstance, setSelectedInstance] =
    useState<ProviderInstance | null>(null);
  const [credentials, setCredentials] = useState<ProviderCredentials>({
    apiKey: "",
    serviceUrl: "",
  });
  const [deploymentType, setDeploymentType] = useState<DeploymentType>("agent");
  const [deploymentName, setDeploymentName] = useState("");
  const [deploymentDescription, setDeploymentDescription] = useState("");
  const [selectedVersionByFlow, setSelectedVersionByFlow] = useState<
    Map<string, { versionId: string; versionTag: string }>
  >(new Map());
  const [attachedConnectionByFlow, setAttachedConnectionByFlow] = useState<
    Map<string, string>
  >(new Map());

  const canGoNext =
    (currentStep === 1 && selectedProvider !== null) ||
    (currentStep === 2 && deploymentName.trim() !== "") ||
    (currentStep === 3 && selectedVersionByFlow.size > 0) ||
    currentStep === 4;

  const handleNext = useCallback(() => {
    setCurrentStep((prev) => (prev < 4 ? prev + 1 : prev));
  }, []);

  const handleBack = useCallback(() => {
    setCurrentStep((prev) => (prev > 1 ? prev - 1 : prev));
  }, []);

  const setSelectedProvider = useCallback((provider: DeploymentProvider) => {
    setSelectedProviderState(provider);
    setSelectedInstance(null);
    setCredentials({ apiKey: "", serviceUrl: "" });
  }, []);

  const handleSelectVersion = useCallback(
    (flowId: string, versionId: string, versionTag: string) => {
      setSelectedVersionByFlow((prev) => {
        const next = new Map(prev);
        next.set(flowId, { versionId, versionTag });
        return next;
      });
    },
    [],
  );

  const value = useMemo<DeploymentStepperContextType>(
    () => ({
      currentStep,
      canGoNext,
      handleNext,
      handleBack,
      selectedProvider,
      setSelectedProvider,
      selectedInstance,
      setSelectedInstance,
      credentials,
      setCredentials,
      deploymentType,
      setDeploymentType,
      deploymentName,
      setDeploymentName,
      deploymentDescription,
      setDeploymentDescription,
      selectedVersionByFlow,
      handleSelectVersion,
      attachedConnectionByFlow,
      setAttachedConnectionByFlow,
    }),
    [
      currentStep,
      canGoNext,
      handleNext,
      handleBack,
      selectedProvider,
      setSelectedProvider,
      selectedInstance,
      credentials,
      deploymentType,
      deploymentName,
      deploymentDescription,
      selectedVersionByFlow,
      handleSelectVersion,
      attachedConnectionByFlow,
    ],
  );

  return (
    <DeploymentStepperContext.Provider value={value}>
      {children}
    </DeploymentStepperContext.Provider>
  );
}

export function useDeploymentStepper() {
  const context = useContext(DeploymentStepperContext);
  if (!context) {
    throw new Error(
      "useDeploymentStepper must be used within a DeploymentStepperProvider",
    );
  }
  return context;
}
