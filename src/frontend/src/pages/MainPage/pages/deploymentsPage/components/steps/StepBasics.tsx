import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";
import type { DeploymentType } from "../../constants";

type DeploymentTypeOption = {
  type: DeploymentType;
  label: string;
  icon: string;
  description: string;
  iconContainerClassName: string;
  iconClassName: string;
};

const DEPLOYMENT_TYPE_OPTIONS: DeploymentTypeOption[] = [
  {
    type: "Agent",
    label: "Agent",
    icon: "Bot",
    description: "Conversational agent with chat interface and tool calling",
    iconContainerClassName: "border-pink-500/20 bg-pink-500/20",
    iconClassName: "text-pink-400",
  },
  {
    type: "MCP",
    label: "MCP Server",
    icon: "Mcp",
    description: "Model Context Protocol server for tool integration",
    iconContainerClassName: "border-blue-500/20 bg-blue-500/20",
    iconClassName: "text-blue-400",
  },
];

type ExistingAgentOption = {
  id: string;
  name: string;
  details: string;
};

const EXISTING_AGENT_OPTIONS: ExistingAgentOption[] = [
  {
    id: "customer-support-agent",
    name: "Customer Support Agent",
    details: "Updated 2 hours ago",
  },
  {
    id: "sales-assistant-agent",
    name: "Sales Assistant Agent",
    details: "Updated yesterday",
  },
  {
    id: "ops-escalation-agent",
    name: "Ops Escalation Agent",
    details: "Updated 3 days ago",
  },
];

type StepBasicsProps = {
  deploymentName: string;
  setDeploymentName: (v: string) => void;
  deploymentDescription: string;
  setDeploymentDescription: (v: string) => void;
  deploymentType: DeploymentType;
  setDeploymentType: (v: DeploymentType) => void;
};

export const StepBasics = ({
  deploymentName,
  setDeploymentName,
  deploymentDescription,
  setDeploymentDescription,
  deploymentType,
  setDeploymentType,
}: StepBasicsProps) => {
  const [agentMode, setAgentMode] = useState<"existing" | "new">("new");
  const [selectedExistingAgentId, setSelectedExistingAgentId] =
    useState<string>(EXISTING_AGENT_OPTIONS[0]?.id ?? "");

  const showAgentModeToggle = deploymentType === "Agent";
  const showExistingAgentSelector =
    deploymentType === "Agent" && agentMode === "existing";
  const showNameAndDescriptionFields =
    deploymentType !== "Agent" || agentMode === "new";

  return (
    <div className="flex w-full flex-col gap-6 overflow-y-auto py-3">
      <div className="flex min-h-0 flex-1 flex-col">
        <span className="text-sm font-medium pb-2">
          Choose Type <span className="text-destructive">*</span>
        </span>
        <div className="grid grid-cols-2 gap-3">
          {DEPLOYMENT_TYPE_OPTIONS.map(
            ({
              type,
              label,
              icon,
              description,
              iconClassName,
              iconContainerClassName,
            }) => (
              <button
                key={type}
                type="button"
                onClick={() => setDeploymentType(type)}
                className={`rounded-lg border bg-muted p-3 text-left ${deploymentType === type
                    ? "border-2 border-foreground"
                    : "border-border hover:border-muted-foreground"
                  }`}
              >
                <div className="flex flex-col">
                  <div className="flex flex-row justify-start items-center">
                    <div
                      className={`mr-3 flex-shrink-0 rounded-lg border p-2 ${iconContainerClassName}`}
                    >
                      <ForwardedIconComponent
                        name={icon}
                        className={`h-6 w-6 ${iconClassName}`}
                      />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">{label}</span>
                      <p className="text-xs text-muted-foreground">
                        {description}
                      </p>
                    </div>
                  </div>
                </div>
              </button>
            ),
          )}
        </div>
      </div>

      {/* {showAgentModeToggle && (
        <div className="rounded-xl border border-border bg-muted p-2">
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setAgentMode("existing")}
              className={`rounded-lg py-2 text-sm transition-colors ${agentMode === "existing"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              Choose existing Agent
            </button>
            <button
              type="button"
              onClick={() => setAgentMode("new")}
              className={`rounded-lg py-2 text-sm transition-colors ${agentMode === "new"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              Add new Agent
            </button>
          </div>
        </div>
      )} */}

      {showExistingAgentSelector && (
        <div className="flex flex-col gap-3">
          <span className="text-sm text-muted-foreground">
            Select from your existing agents
          </span>
          {EXISTING_AGENT_OPTIONS.map((agent) => {
            const isSelected = selectedExistingAgentId === agent.id;
            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => setSelectedExistingAgentId(agent.id)}
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
                    {agent.name}
                  </span>
                  <span className="text-sm text-muted-foreground leading-tight">
                    {agent.details}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      )}

      {showNameAndDescriptionFields && (
        <>
          <div className="flex flex-col">
            <span className="text-sm font-medium pb-2">
              {deploymentType === "Agent"
                ? "Agent Name"
                : deploymentType === "MCP"
                  ? "MCP Server Name"
                  : "Name Deployment"}{" "}
              <span className="text-destructive">*</span>
            </span>
            <Input
              placeholder="e.g., Production Sales Agent"
              className="bg-muted"
              value={deploymentName}
              onChange={(e) => setDeploymentName(e.target.value)}
            />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium pb-2">Description</span>
            <Textarea
              placeholder="Describe what this deployment does..."
              value={deploymentDescription}
              onChange={(e) => setDeploymentDescription(e.target.value)}
              rows={3}
              className="resize-none placeholder:text-placeholder-foreground bg-muted"
            />
          </div>
        </>
      )}
    </div>
  );
};
