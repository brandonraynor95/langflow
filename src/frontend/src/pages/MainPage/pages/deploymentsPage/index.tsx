import { useEffect, useState } from "react";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import DeploymentStepperModal from "./components/DeploymentStepperModal";
import DeploymentsEmptyState from "./components/DeploymentsEmptyState";
import DeploymentsLoadingSkeleton from "./components/DeploymentsLoadingSkeleton";
import DeploymentsTable from "./components/DeploymentsTable";
import SubTabToggle, { type DeploymentSubTab } from "./components/SubTabToggle";
import { MOCK_DEPLOYMENTS } from "./mock-data";

export default function DeploymentsPage() {
  const [activeSubTab, setActiveSubTab] =
    useState<DeploymentSubTab>("deployments");
  const [isLoading, setIsLoading] = useState(true);
  const [stepperOpen, setStepperOpen] = useState(false);

  // Simulate loading with mock data
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  const deployments = MOCK_DEPLOYMENTS;
  const isEmpty = deployments.length === 0;

  return (
    <div className="flex flex-col gap-4 pt-4">
      <div className="flex items-center justify-between">
        <SubTabToggle activeTab={activeSubTab} onTabChange={setActiveSubTab} />
        <Button
          onClick={() => setStepperOpen(true)}
          data-testid="new-deployment-btn"
        >
          <ForwardedIconComponent name="Plus" className="h-4 w-4" />
          New Deployment
        </Button>
      </div>

      {activeSubTab === "deployments" &&
        (isLoading ? (
          <DeploymentsLoadingSkeleton />
        ) : isEmpty ? (
          <DeploymentsEmptyState
            onCreateDeployment={() => setStepperOpen(true)}
          />
        ) : (
          <DeploymentsTable deployments={deployments} />
        ))}

      {activeSubTab === "providers" && (
        <div className="py-24 text-center text-sm text-muted-foreground">
          Deployment Providers coming soon
        </div>
      )}

      <DeploymentStepperModal open={stepperOpen} setOpen={setStepperOpen} />
    </div>
  );
}
