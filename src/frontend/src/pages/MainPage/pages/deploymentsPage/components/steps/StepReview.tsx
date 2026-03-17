import { Badge } from "@/components/ui/badge";
import type { DeploymentType, EnvVar } from "../../constants";

type SelectedItem = { name: string };

type StepReviewProps = {
  deploymentType: DeploymentType;
  deploymentName: string;
  deploymentDescription: string;
  selectedItems: SelectedItem[];
  envVars: EnvVar[];
  providerName?: string;
  selectedAgentName?: string;
};

const MOCK_REVIEW_DATA = {
  providerName: "watsonx Orchestrate",
  agentName: "Best Agent",
  description: "problem solver",
  flows: [{ name: "Qualify Lead (v2)" }],
};

const splitFlowNameAndVersion = (value: string) => {
  const match = value.match(/^(.*)\s+\(([^)]+)\)$/);
  if (!match) {
    return { flowName: value, versionLabel: "" };
  }
  return {
    flowName: match[1].trim(),
    versionLabel: match[2].trim(),
  };
};

export const StepReview = ({
  deploymentType,
  deploymentName,
  deploymentDescription,
  selectedItems,
  envVars,
  providerName,
  selectedAgentName,
}: StepReviewProps) => {
  void deploymentType;
  void envVars;
  const displayProviderName =
    providerName?.trim() || MOCK_REVIEW_DATA.providerName;
  const displayAgentName =
    deploymentName.trim() ||
    selectedAgentName?.trim() ||
    MOCK_REVIEW_DATA.agentName;
  const displayDescription =
    deploymentDescription.trim() || MOCK_REVIEW_DATA.description;
  const reviewItems =
    selectedItems.length > 0 ? selectedItems : MOCK_REVIEW_DATA.flows;

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-8 rounded-2xl border bg-muted p-5">
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-normal leading-none text-muted-foreground">
            Provider
          </span>
          <span className="text-base font-normal leading-none text-foreground">
            {displayProviderName}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-normal leading-none text-muted-foreground">
            Agent Name
          </span>
          <span className="text-base font-normal leading-none text-foreground">
            {displayAgentName}
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-normal leading-none text-muted-foreground">
            Description
          </span>
          <span className="text-base font-normal leading-none text-foreground">
            {displayDescription}
          </span>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-sm font-normal leading-none text-muted-foreground">
            Flows ({reviewItems.length})
          </span>
          {reviewItems.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {reviewItems.map(({ name }) => {
                const { flowName, versionLabel } = splitFlowNameAndVersion(name);
                return (
                  <li
                    key={name}
                    className="flex items-center justify-between rounded-xl border px-4 py-3 bg-background"
                  >
                    <span className="text-sm font-normal leading-none text-foreground">
                      {flowName}
                    </span>
                    {versionLabel && (
                      <Badge variant="secondary" size="sq">
                        {versionLabel}
                      </Badge>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      </div>
    </div>
  );
};
