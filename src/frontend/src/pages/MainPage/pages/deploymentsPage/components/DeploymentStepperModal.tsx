import ForwardedIconComponent from "@/components/common/genericIconComponent";
import StepperModal, {
  StepperModalFooter,
} from "@/modals/stepperModal/StepperModal";
import { StepAttachFlows } from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepAttachFlows";
import { StepBasics } from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepBasics";
import { StepProvider } from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepProvider";
import { StepReview } from "@/pages/MainPage/pages/deploymentsPage/components/steps/StepReview";
import type { Dispatch, SetStateAction } from "react";
import type { DeploymentType, EnvVar } from "../constants";
import { PROVIDER_OPTIONS, TOTAL_STEPS } from "../constants";
import type { FlowCheckpointGroup } from "../types";
import { DeployFlowStepper } from "./DeployFlowStepper";

const STEP_LABELS = ["Provider", "Type", "Attach Flows", "Review"];

type DeploymentStepperModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentStep: number;
  deploymentType: DeploymentType;
  setDeploymentType: (type: DeploymentType) => void;
  deploymentName: string;
  setDeploymentName: (name: string) => void;
  deploymentDescription: string;
  setDeploymentDescription: (desc: string) => void;
  deploymentAccountId: string;
  setDeploymentAccountId: (value: string) => void;
  selectedItems: Set<string>;
  toggleItem: (id: string) => void;
  checkpointGroups: FlowCheckpointGroup[];
  envVars: EnvVar[];
  setEnvVars: Dispatch<SetStateAction<EnvVar[]>>;
  detectedVarCount: number;
  selectedReviewItems: { name: string }[];
  providerName?: string;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
};

export const DeploymentStepperModal = ({
  open,
  onOpenChange,
  currentStep,
  deploymentType,
  setDeploymentType,
  deploymentName,
  setDeploymentName,
  deploymentDescription,
  setDeploymentDescription,
  deploymentAccountId,
  setDeploymentAccountId,
  selectedItems,
  toggleItem,
  checkpointGroups,
  envVars,
  setEnvVars,
  detectedVarCount,
  selectedReviewItems,
  providerName,
  onBack,
  onNext,
  onSubmit,
}: DeploymentStepperModalProps) => {
  const selectedAgentName = checkpointGroups.find((g) =>
    selectedItems.has(g.flowId),
  )?.flowName;

  return (
    <StepperModal
      className="p-2"
      open={open}
      onOpenChange={onOpenChange}
      currentStep={currentStep}
      totalSteps={TOTAL_STEPS}
      showProgress={false}
      description={""}
      title={
        currentStep === 1
          ? "Provider"
          : currentStep === 2
            ? "Deployment Type"
            : currentStep === 3
              ? "Attach Flows"
              : "Review Deployment"
      }
      bgClassName="bg-secondary"
      width="w-[752px]"
      height="h-[671px]"
      contentClassName="bg-background "
      stepLabels={STEP_LABELS}
      onBack={() => onOpenChange(false)}
      closeButtonClassName="top-[20px] right-4"
      backLabel="Back to Deployments"
      footer={
        <StepperModalFooter
          currentStep={currentStep}
          totalSteps={TOTAL_STEPS}
          onBack={onBack}
          onNext={() => {
            onNext();
          }}
          onSubmit={onSubmit}
          submitLabel={
            <>
              <ForwardedIconComponent name="Rocket" className="h-4 w-4" />{" "}
              Deploy
            </>
          }
          nextLabel="Next"
        />
      }
    >
      <DeployFlowStepper currentStep={currentStep} labels={STEP_LABELS} />
      {currentStep === 1 && (
        <StepProvider
          value={{
            apiKey: deploymentName,
            serviceUrl: deploymentDescription,
            accountId: deploymentAccountId,
          }}
          onChange={{
            setApiKey: setDeploymentName,
            setServiceUrl: setDeploymentDescription,
            setAccountId: setDeploymentAccountId,
          }}
          config={{
            providerOptions: PROVIDER_OPTIONS,
            providerGridClassName: "grid-cols-2 gap-4",
          }}
        />
      )}
      {currentStep === 2 && (
        <StepBasics
          deploymentName={deploymentName}
          setDeploymentName={setDeploymentName}
          deploymentDescription={deploymentDescription}
          setDeploymentDescription={setDeploymentDescription}
          deploymentType={deploymentType}
          setDeploymentType={setDeploymentType}
        />
      )}

      {currentStep === 3 && (
        <StepAttachFlows
          selectedItems={selectedItems}
          toggleItem={toggleItem}
          flows={checkpointGroups}
        />
      )}
      {currentStep === 4 && (
        <StepReview
          deploymentType={deploymentType}
          deploymentName={deploymentName}
          deploymentDescription={deploymentDescription}
          selectedItems={selectedReviewItems}
          envVars={envVars}
          providerName={providerName}
          selectedAgentName={selectedAgentName}
        />
      )}
    </StepperModal>
  );
};
