import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/utils/utils";
import { useDeploymentStepper } from "../contexts/deployment-stepper-context";
import type { DeploymentType } from "../types";

const TYPE_OPTIONS: {
  type: DeploymentType;
  label: string;
  description: string;
  icon: string;
  iconBg: string;
}[] = [
  {
    type: "agent",
    label: "Agent",
    description: "Conversational agent with chat interface and tool calling",
    icon: "MessageSquare",
    iconBg: "border-accent-pink-foreground/20 bg-accent-pink-foreground/20",
  },
  {
    type: "mcp",
    label: "MCP Server",
    description: "Model Context Protocol server for tool integration",
    icon: "Layers",
    iconBg: "border-accent-blue-foreground/20 bg-accent-blue-foreground/20",
  },
];

export default function StepType() {
  const {
    deploymentType,
    setDeploymentType,
    deploymentName,
    setDeploymentName,
    deploymentDescription,
    setDeploymentDescription,
  } = useDeploymentStepper();
  return (
    <div className="flex w-full flex-col gap-6 overflow-y-auto py-3">
      <h2 className="text-lg font-semibold">Deployment Type</h2>

      <div className="flex flex-col gap-3">
        <span className="text-sm font-medium">
          Choose Type <span className="text-destructive">*</span>
        </span>
        <div
          className="grid grid-cols-2 gap-3"
          role="radiogroup"
          aria-label="Deployment type"
        >
          {TYPE_OPTIONS.map((option) => (
            <button
              key={option.type}
              type="button"
              role="radio"
              aria-checked={deploymentType === option.type}
              data-testid={`deployment-type-${option.type}`}
              onClick={() => setDeploymentType(option.type)}
              className={cn(
                "flex items-start gap-3 rounded-lg border bg-muted p-3 text-left transition-colors",
                deploymentType === option.type
                  ? "border-2 border-foreground"
                  : "border-border hover:border-muted-foreground",
              )}
            >
              <div
                className={cn(
                  "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border p-2",
                  option.iconBg,
                )}
              >
                <ForwardedIconComponent
                  name={option.icon}
                  className="h-5 w-5"
                />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-medium">{option.label}</span>
                <p className="text-xs text-muted-foreground">
                  {option.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col">
        <span className="pb-2 text-sm font-medium">
          {deploymentType === "agent" ? "Agent" : "Server"} Name{" "}
          <span className="text-destructive">*</span>
        </span>
        <Input
          placeholder="e.g., Sales Bot"
          className="bg-muted"
          value={deploymentName}
          onChange={(e) => setDeploymentName(e.target.value)}
        />
      </div>

      <div className="flex flex-col">
        <span className="pb-2 text-sm font-medium">Description</span>
        <Textarea
          placeholder="Describe the agent's purpose..."
          rows={3}
          className="resize-none bg-muted placeholder:text-placeholder-foreground"
          value={deploymentDescription}
          onChange={(e) => setDeploymentDescription(e.target.value)}
        />
      </div>
    </div>
  );
}
