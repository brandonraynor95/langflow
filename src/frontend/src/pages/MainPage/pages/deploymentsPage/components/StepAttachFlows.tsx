import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useGetFlowVersions } from "@/controllers/API/queries/flow-version/use-get-flow-versions";
import { useGetRefreshFlowsQuery } from "@/controllers/API/queries/flows/use-get-refresh-flows-query";
import { useFolderStore } from "@/stores/foldersStore";
import type { FlowType } from "@/types/flow";
import type { FlowVersionEntry } from "@/types/flow/version";
import { cn } from "@/utils/utils";
import { useDeploymentStepper } from "../contexts/DeploymentStepperContext";
import { MOCK_CONNECTIONS } from "../mock-data";

export interface ConnectionItem {
  id: string;
  name: string;
  variableCount: number;
}

type RightPanelView = "versions" | "connections";
type ConnectionTab = "available" | "create";

export default function StepAttachFlows() {
  const {
    selectedVersionByFlow,
    handleSelectVersion: onSelectVersion,
    attachedConnectionByFlow,
    setAttachedConnectionByFlow: onAttachConnection,
  } = useDeploymentStepper();

  const { folderId } = useParams();
  const myCollectionId = useFolderStore((state) => state.myCollectionId);
  const currentFolderId = folderId ?? myCollectionId;

  const { data: flowsData } = useGetRefreshFlowsQuery(
    {
      get_all: true,
      remove_example_flows: true,
    },
    { enabled: !!currentFolderId },
  );
  const flows = useMemo(() => {
    const list = Array.isArray(flowsData) ? flowsData : [];
    return list.filter(
      (f) => !f.is_component && f.folder_id === currentFolderId,
    );
  }, [flowsData, currentFolderId]);
  const connections = MOCK_CONNECTIONS;

  const [selectedFlowId, setSelectedFlowId] = useState<string | null>(
    flows[0]?.id ?? null,
  );
  const [pendingVersion, setPendingVersion] = useState<string | null>(null);
  const [rightPanel, setRightPanel] = useState<RightPanelView>("versions");
  const [connectionTab, setConnectionTab] =
    useState<ConnectionTab>("available");
  const [selectedConnection, setSelectedConnection] = useState<string | null>(
    null,
  );
  const [newConnectionName, setNewConnectionName] = useState("");
  const [newConnectionDescription, setNewConnectionDescription] = useState("");
  const [envVars, setEnvVars] = useState<{ key: string; value: string }[]>([
    { key: "", value: "" },
  ]);

  const { data: versionResponse, isLoading: isLoadingVersions } =
    useGetFlowVersions(
      { flowId: selectedFlowId! },
      { enabled: !!selectedFlowId },
    );
  const versions = versionResponse?.entries ?? [];

  const selectedFlow = flows.find((f) => f.id === selectedFlowId);

  const handleAttachFlow = () => {
    if (selectedFlowId && pendingVersion) {
      const version = versions.find((v) => v.id === pendingVersion);
      onSelectVersion(
        selectedFlowId,
        pendingVersion,
        version?.version_tag ?? "",
      );
      setPendingVersion(null);
      setRightPanel("connections");
      setSelectedConnection(
        attachedConnectionByFlow.get(selectedFlowId) ?? null,
      );
    }
  };

  const handleAttachConnection = () => {
    if (!selectedFlowId) return;
    if (connectionTab === "available" && selectedConnection) {
      onAttachConnection((prev) => {
        const next = new Map(prev);
        next.set(selectedFlowId, selectedConnection);
        return next;
      });
      setRightPanel("versions");
      setSelectedConnection(null);
    }
    // TODO: handle "create" tab
  };

  const handleChangeFlow = () => {
    setRightPanel("versions");
    setSelectedConnection(null);
  };

  const handleSelectFlow = (flowId: string) => {
    setSelectedFlowId(flowId);
    setPendingVersion(null);
    setRightPanel("versions");
  };

  const handleAddEnvVar = () => {
    setEnvVars([...envVars, { key: "", value: "" }]);
  };

  const handleEnvVarChange = (
    index: number,
    field: "key" | "value",
    val: string,
  ) => {
    setEnvVars((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: val } : item)),
    );
  };

  const getVersionLabel = (flowId: string) => {
    const entry = selectedVersionByFlow.get(flowId);
    if (!entry) return null;
    return entry.versionTag || null;
  };

  const isFlowAttached = (flowId: string) =>
    attachedConnectionByFlow.has(flowId);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 py-3">
      <h2 className="text-lg font-semibold">Attach Flows</h2>

      <div className="flex min-h-0 flex-1 overflow-hidden rounded-xl border border-border">
        {/* Left panel — flow list */}
        <div className="flex w-[280px] flex-shrink-0 flex-col border-r border-border">
          <div className="border-b border-border p-4 text-sm text-muted-foreground">
            Available Flows
          </div>
          <div className="flex-1 space-y-1 overflow-y-auto p-2">
            {flows.map((flow) => {
              const versionLabel = getVersionLabel(flow.id);
              const attached = isFlowAttached(flow.id);
              return (
                <button
                  key={flow.id}
                  type="button"
                  onClick={() => handleSelectFlow(flow.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg p-3 text-left transition-colors",
                    selectedFlowId === flow.id
                      ? "bg-muted"
                      : "hover:bg-muted/60",
                  )}
                >
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg border border-border bg-muted">
                    <ForwardedIconComponent
                      name={flow.icon ?? "Workflow"}
                      className="h-4 w-4 text-muted-foreground"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-sm font-semibold">
                        {flow.name}
                      </span>
                      {versionLabel && (
                        <Badge
                          variant="secondaryStatic"
                          size="tag"
                          className="bg-accent-purple-muted text-accent-purple-muted-foreground"
                        >
                          {versionLabel}
                        </Badge>
                      )}
                      {attached && (
                        <Badge
                          variant="secondaryStatic"
                          size="tag"
                          className="bg-accent-blue-muted text-accent-blue-muted-foreground"
                        >
                          ATTACHED
                        </Badge>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-1 flex-col">
          {rightPanel === "versions" ? (
            <VersionPanel
              selectedFlow={selectedFlow}
              versions={versions}
              isLoadingVersions={isLoadingVersions}
              pendingVersion={pendingVersion}
              selectedVersionByFlow={selectedVersionByFlow}
              attachedConnectionByFlow={attachedConnectionByFlow}
              onSelectPending={(id) =>
                setPendingVersion(pendingVersion === id ? null : id)
              }
              onAttach={handleAttachFlow}
            />
          ) : (
            <ConnectionPanel
              connectionTab={connectionTab}
              onTabChange={setConnectionTab}
              connections={connections}
              selectedConnection={selectedConnection}
              onSelectConnection={setSelectedConnection}
              newConnectionName={newConnectionName}
              onNameChange={setNewConnectionName}
              newConnectionDescription={newConnectionDescription}
              onDescriptionChange={setNewConnectionDescription}
              envVars={envVars}
              onEnvVarChange={handleEnvVarChange}
              onAddEnvVar={handleAddEnvVar}
              onChangeFlow={handleChangeFlow}
              onAttachConnection={handleAttachConnection}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Version selection panel ── */

function VersionPanel({
  selectedFlow,
  versions,
  isLoadingVersions,
  pendingVersion,
  selectedVersionByFlow,
  attachedConnectionByFlow,
  onSelectPending,
  onAttach,
}: {
  selectedFlow: FlowType | undefined;
  versions: FlowVersionEntry[];
  isLoadingVersions: boolean;
  pendingVersion: string | null;
  selectedVersionByFlow: Map<string, { versionId: string; versionTag: string }>;
  attachedConnectionByFlow: Map<string, string>;
  onSelectPending: (id: string) => void;
  onAttach: () => void;
}) {
  if (!selectedFlow) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Select a flow to see versions
      </div>
    );
  }

  const attachedEntry = selectedVersionByFlow.get(selectedFlow.id);
  const hasConnection = attachedConnectionByFlow.has(selectedFlow.id);

  return (
    <>
      <div className="border-b border-border p-4 text-sm text-muted-foreground">
        Select a version to attach to this deployment
      </div>
      <div className="flex flex-1 flex-col overflow-hidden px-4 py-2">
        <h3 className="py-2 text-lg font-semibold">{selectedFlow.name}</h3>
        <div className="flex-1 space-y-3 overflow-y-auto py-3">
          {isLoadingVersions ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              Loading versions...
            </div>
          ) : versions.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              No versions found
            </div>
          ) : (
            versions.map((version) => {
              const isAttachedVersion = attachedEntry?.versionId === version.id;
              const isPending = pendingVersion === version.id;
              const isSelected = isPending;
              return (
                <button
                  key={version.id}
                  type="button"
                  onClick={() => onSelectPending(version.id)}
                  className={cn(
                    "flex w-full items-center gap-4 rounded-xl border bg-muted p-3 text-left transition-colors",
                    isSelected
                      ? "border-primary"
                      : "border-transparent hover:border-border",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded",
                      isSelected
                        ? "bg-primary text-primary-foreground"
                        : "border border-muted-foreground bg-background",
                    )}
                  >
                    {isSelected && (
                      <ForwardedIconComponent
                        name="Check"
                        className="h-3.5 w-3.5"
                      />
                    )}
                  </span>
                  <span className="flex flex-col">
                    <span className="flex items-center gap-2 text-sm font-medium leading-tight">
                      {version.version_tag}
                      {isAttachedVersion && hasConnection && (
                        <Badge
                          variant="secondaryStatic"
                          size="tag"
                          className="bg-accent-blue-muted text-accent-blue-muted-foreground"
                        >
                          ATTACHED
                        </Badge>
                      )}
                    </span>
                    <span className="text-sm leading-tight text-muted-foreground">
                      Created:{" "}
                      {new Date(version.created_at).toLocaleDateString()}
                    </span>
                  </span>
                </button>
              );
            })
          )}
        </div>
        <Button
          className="w-full"
          disabled={!pendingVersion}
          onClick={onAttach}
        >
          Attach Flow
        </Button>
      </div>
    </>
  );
}

/* ── Connection panel (after attaching a flow) ── */

function ConnectionPanel({
  connectionTab,
  onTabChange,
  connections,
  selectedConnection,
  onSelectConnection,
  newConnectionName,
  onNameChange,
  newConnectionDescription,
  onDescriptionChange,
  envVars,
  onEnvVarChange,
  onAddEnvVar,
  onChangeFlow,
  onAttachConnection,
}: {
  connectionTab: ConnectionTab;
  onTabChange: (tab: ConnectionTab) => void;
  connections: ConnectionItem[];
  selectedConnection: string | null;
  onSelectConnection: (id: string | null) => void;
  newConnectionName: string;
  onNameChange: (v: string) => void;
  newConnectionDescription: string;
  onDescriptionChange: (v: string) => void;
  envVars: { key: string; value: string }[];
  onEnvVarChange: (index: number, field: "key" | "value", val: string) => void;
  onAddEnvVar: () => void;
  onChangeFlow: () => void;
  onAttachConnection: () => void;
}) {
  const canAttachConnection =
    connectionTab === "available"
      ? selectedConnection !== null
      : newConnectionName.trim() !== "";

  return (
    <>
      <div className="border-b border-border p-4 text-sm text-muted-foreground">
        Select or Create New Connection
      </div>
      <div className="flex flex-1 flex-col overflow-hidden px-4 py-4">
        {/* Tab toggle */}
        <div className="rounded-xl border border-border bg-muted p-1">
          <div className="grid grid-cols-2">
            {(["available", "create"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => onTabChange(tab)}
                className={cn(
                  "rounded-lg py-2 text-sm transition-colors",
                  connectionTab === tab
                    ? "bg-background"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {tab === "available"
                  ? "Available Connections"
                  : "Create Connection"}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div className="mt-4 flex-1 overflow-y-auto">
          {connectionTab === "available" ? (
            <div className="space-y-3">
              {connections.map((conn) => {
                const isSelected = selectedConnection === conn.id;
                return (
                  <button
                    key={conn.id}
                    type="button"
                    onClick={() =>
                      onSelectConnection(isSelected ? null : conn.id)
                    }
                    className={cn(
                      "flex w-full items-center gap-4 rounded-xl border bg-muted p-3 text-left transition-colors",
                      isSelected
                        ? "border-primary"
                        : "border-transparent hover:border-border",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded",
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "border border-muted-foreground bg-background",
                      )}
                    >
                      {isSelected && (
                        <ForwardedIconComponent
                          name="Check"
                          className="h-3.5 w-3.5"
                        />
                      )}
                    </span>
                    <span className="flex flex-col">
                      <span className="text-sm font-medium leading-tight">
                        {conn.name}
                      </span>
                      <span className="text-sm leading-tight text-muted-foreground">
                        {conn.variableCount} variables
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col">
                <span className="pb-2 text-sm font-medium">
                  Connection Name<span className="text-destructive">*</span>
                </span>
                <Input
                  placeholder="e.g., SALES_BOT_PROD"
                  className="bg-muted"
                  value={newConnectionName}
                  onChange={(e) => onNameChange(e.target.value)}
                />
              </div>
              <div className="flex flex-col">
                <span className="pb-2 text-sm font-medium">Description</span>
                <Input
                  placeholder="e.g., Production sales bot connection"
                  className="bg-muted"
                  value={newConnectionDescription}
                  onChange={(e) => onDescriptionChange(e.target.value)}
                />
              </div>
              <div className="flex flex-col">
                <span className="pb-2 text-sm font-medium">
                  Environment Variables
                  <span className="text-destructive">*</span>
                </span>
                <div className="space-y-2">
                  {envVars.map((envVar, index) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: This is a simple form, using index as key is acceptable here
                    <div key={index} className="grid grid-cols-2 gap-2">
                      <Input
                        placeholder="Key"
                        className="bg-muted"
                        value={envVar.key}
                        onChange={(e) =>
                          onEnvVarChange(index, "key", e.target.value)
                        }
                      />
                      <Input
                        placeholder="Value"
                        className="bg-muted"
                        value={envVar.value}
                        onChange={(e) =>
                          onEnvVarChange(index, "value", e.target.value)
                        }
                      />
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={onAddEnvVar}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    + Add variable
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer buttons */}
        <div className="flex items-center gap-3 pt-4">
          <Button variant="outline" onClick={onChangeFlow}>
            Change Flow
          </Button>
          <Button
            className="flex-1"
            disabled={!canAttachConnection}
            onClick={onAttachConnection}
          >
            Attach Connection to Flow
          </Button>
        </div>
      </div>
    </>
  );
}
