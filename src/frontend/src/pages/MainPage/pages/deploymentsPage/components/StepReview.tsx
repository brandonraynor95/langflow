import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { useDeploymentStepper } from "../contexts/DeploymentStepperContext";
import { MOCK_CONNECTIONS, MOCK_FLOWS_WITH_VERSIONS } from "../mock-data";

function ReviewField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-base font-normal text-foreground">{value}</span>
    </div>
  );
}

export default function StepReview() {
  const {
    selectedProvider: provider,
    deploymentType,
    deploymentName,
    deploymentDescription,
    selectedVersionByFlow,
    attachedConnectionByFlow,
  } = useDeploymentStepper();
  const flows = MOCK_FLOWS_WITH_VERSIONS;
  const connections = MOCK_CONNECTIONS;
  const reviewFlows = Array.from(selectedVersionByFlow.entries()).map(
    ([flowId, versionId]) => {
      const flow = flows.find((f) => f.id === flowId);
      const version = flow?.versions.find((v) => v.id === versionId);
      const connectionId = attachedConnectionByFlow.get(flowId);
      const connection = connectionId
        ? connections.find((c) => c.id === connectionId)
        : null;
      return {
        flowId,
        flowName: flow?.name ?? "Unknown",
        versionLabel: version?.label ?? "—",
        versionDate: version?.lastUpdated ?? "—",
        connectionName: connection?.name ?? "Not configured",
      };
    },
  );

  return (
    <div className="flex flex-col gap-6 py-3">
      <h2 className="text-lg font-semibold">Review Deployment</h2>
      <p className="text-sm text-muted-foreground">
        Review the details of your deployment before finalizing
      </p>

      <div className="flex flex-col gap-8 rounded-2xl border border-border bg-muted p-5">
        <ReviewField label="Provider" value={provider?.name ?? "—"} />
        <ReviewField
          label={deploymentType === "agent" ? "Agent Name" : "Server Name"}
          value={deploymentName || "—"}
        />
        {deploymentDescription && (
          <ReviewField label="Description" value={deploymentDescription} />
        )}

        <div className="flex flex-col gap-2">
          <span className="text-sm text-muted-foreground">
            Flows ({reviewFlows.length})
          </span>
          <Accordion type="multiple" className="flex flex-col gap-3">
            {reviewFlows.map((item) => (
              <AccordionItem
                key={item.flowId}
                value={item.flowId}
                className="rounded-xl border border-border bg-background px-4"
              >
                <AccordionTrigger className="py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground">
                      {item.flowName}
                    </span>
                    <Badge
                      variant="secondaryStatic"
                      size="tag"
                      className="bg-accent-purple-muted text-accent-purple-muted-foreground"
                    >
                      {item.versionLabel}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="flex flex-col gap-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Version</span>
                      <span className="text-foreground">
                        {item.versionLabel}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">
                        Last updated
                      </span>
                      <span className="text-foreground">
                        {item.versionDate}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Connection</span>
                      <span className="text-foreground">
                        {item.connectionName}
                      </span>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </div>
  );
}
