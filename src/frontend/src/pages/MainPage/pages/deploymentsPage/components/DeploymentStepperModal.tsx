import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DeploymentStepperProvider,
  useDeploymentStepper,
} from "../contexts/DeploymentStepperContext";
import DeploymentStepper from "./DeploymentStepper";
import StepAttachFlows from "./StepAttachFlows";
import StepProvider from "./StepProvider";
import StepReview from "./StepReview";
import StepType from "./StepType";

interface DeploymentStepperModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export default function DeploymentStepperModal({
  open,
  setOpen,
}: DeploymentStepperModalProps) {
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="flex h-[85vh] w-[900px] !max-w-none flex-col gap-0 overflow-hidden border-none bg-transparent p-0 shadow-none"
        closeButtonClassName="top-5 right-4"
      >
        <DeploymentStepperProvider>
          <DeploymentStepperModalContent setOpen={setOpen} />
        </DeploymentStepperProvider>
      </DialogContent>
    </Dialog>
  );
}

function DeploymentStepperModalContent({
  setOpen,
}: {
  setOpen: (open: boolean) => void;
}) {
  const { currentStep, canGoNext, handleNext, handleBack } =
    useDeploymentStepper();

  return (
    <>
      <DialogTitle className="sr-only">Create New Deployment</DialogTitle>
      <DialogDescription className="sr-only">
        Step {currentStep} of 4
      </DialogDescription>

      {/* Title + Stepper */}
      <div className="flex flex-col gap-4 px-6 pt-6">
        <h2 className="text-center text-2xl font-semibold">
          Create New Deployment
        </h2>
        <DeploymentStepper />
      </div>

      {/* Content box: step content + footer */}
      <div className="mx-4 mb-4 mt-4 flex flex-1 flex-col overflow-hidden rounded-lg border border-border bg-background">
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-2">
          {currentStep === 1 && <StepProvider />}
          {currentStep === 2 && <StepType />}
          {currentStep === 3 && <StepAttachFlows />}
          {currentStep === 4 && <StepReview />}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 1}
            className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            Back
          </button>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleNext}
              disabled={!canGoNext}
              data-testid="deployment-stepper-next"
            >
              {currentStep === 4 ? (
                <>
                  <ForwardedIconComponent name="Rocket" className="h-4 w-4" />
                  Deploy
                </>
              ) : (
                "Next"
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
