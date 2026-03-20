import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/utils/utils";
import type { Deployment, DeploymentHealth, DeploymentType } from "../types";

interface DeploymentsTableProps {
  deployments: Deployment[];
}

const TYPE_CONFIG: Record<DeploymentType, { color: string; dotColor: string }> =
  {
    agent: { color: "border-l-error", dotColor: "" },
    mcp: { color: "border-l-accent-emerald", dotColor: "" },
  };

const HEALTH_CONFIG: Record<
  DeploymentHealth,
  { color: string; label: string }
> = {
  healthy: { color: "text-accent-emerald", label: "Healthy" },
  unhealthy: { color: "text-error", label: "Unhealthy" },
  pending: { color: "text-warning", label: "Pending" },
};

function TypeBadge({ type }: { type: DeploymentType }) {
  const config = TYPE_CONFIG[type];
  return (
    <Badge
      variant="secondaryStatic"
      size="sq"
      className={cn("border-l-2", config.color)}
    >
      {type === "agent" ? "Agent" : "MCP"}
    </Badge>
  );
}

function StatusBadge({ status }: { status: Deployment["status"] }) {
  return (
    <Badge
      variant="secondaryStatic"
      size="sq"
      className={
        status === "production"
          ? "bg-accent-blue-muted text-accent-blue-muted-foreground"
          : ""
      }
    >
      {status === "production" ? "Production" : "Draft"}
    </Badge>
  );
}

function HealthIndicator({ health }: { health: DeploymentHealth }) {
  const config = HEALTH_CONFIG[health];
  return (
    <div className="flex items-center gap-2">
      <span className={cn("text-lg leading-none", config.color)}>&bull;</span>
      <span className="text-sm">{config.label}</span>
    </div>
  );
}

export default function DeploymentsTable({
  deployments,
}: DeploymentsTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Health</TableHead>
          <TableHead>Attached</TableHead>
          <TableHead>Provider</TableHead>
          <TableHead>Last Modified</TableHead>
          <TableHead>Test</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {deployments.map((deployment) => (
          <TableRow key={deployment.id}>
            <TableCell>
              <div className="flex flex-col">
                <span className="font-medium">{deployment.name}</span>
                <span className="text-xs text-muted-foreground">
                  {deployment.url}
                </span>
              </div>
            </TableCell>
            <TableCell>
              <TypeBadge type={deployment.type} />
            </TableCell>
            <TableCell>
              <StatusBadge status={deployment.status} />
            </TableCell>
            <TableCell>
              <HealthIndicator health={deployment.health} />
            </TableCell>
            <TableCell>
              <span className="text-sm">
                {deployment.attachedCount}{" "}
                {deployment.attachedCount === 1 ? "item" : "items"}
              </span>
            </TableCell>
            <TableCell>
              <span className="text-sm">{deployment.provider}</span>
            </TableCell>
            <TableCell>
              <div className="flex flex-col">
                <span className="text-sm">{deployment.lastModified}</span>
                <span className="text-xs text-muted-foreground">
                  by {deployment.lastModifiedBy}
                </span>
              </div>
            </TableCell>
            <TableCell>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label={`Test ${deployment.name}`}
              >
                <ForwardedIconComponent name="Play" className="h-4 w-4" />
              </Button>
            </TableCell>
            <TableCell>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label={`Actions for ${deployment.name}`}
              >
                <ForwardedIconComponent
                  name="EllipsisVertical"
                  className="h-4 w-4"
                />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
