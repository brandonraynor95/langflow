import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

type CheckpointAttachItem = {
  id: string;
  name: string;
  updatedDate: string;
};

type FlowAttachItem = {
  flowId: string;
  flowName: string;
  checkpoints: CheckpointAttachItem[];
};

type MockFlowVersion = {
  id: string;
  label: string;
  updatedAt: string;
};

type MockFlowItem = {
  id: string;
  name: string;
  versions: MockFlowVersion[];
  attachedVersionId?: string;
};

type StepAttachFlowsProps = {
  selectedItems: Set<string>;
  toggleItem: (id: string) => void;
  flows: FlowAttachItem[];
};

const MOCK_FLOW_ITEMS: MockFlowItem[] = [
  {
    id: "qualify-lead",
    name: "Qualify Lead",
    attachedVersionId: "qualify-lead-v2",
    versions: [
      { id: "qualify-lead-v7", label: "v7", updatedAt: "2026-02-22" },
      { id: "qualify-lead-v6", label: "v6", updatedAt: "2026-02-21" },
      { id: "qualify-lead-v5", label: "v5", updatedAt: "2026-02-20" },
      { id: "qualify-lead-v4", label: "v4", updatedAt: "2026-02-19" },
      { id: "qualify-lead-v3", label: "v3", updatedAt: "2026-02-18" },
      { id: "qualify-lead-v2", label: "v2", updatedAt: "2026-02-15" },
      { id: "qualify-lead-v1", label: "v1", updatedAt: "2026-02-10" },
    ],
  },
  {
    id: "summarize-call-notes",
    name: "Summarize Call Notes",
    versions: [
      { id: "summarize-call-notes-v2", label: "v2", updatedAt: "2026-02-16" },
      { id: "summarize-call-notes-v1", label: "v1", updatedAt: "2026-02-08" },
    ],
  },
  {
    id: "create-ticket",
    name: "Create Ticket",
    versions: [
      { id: "create-ticket-v4", label: "v4", updatedAt: "2026-02-17" },
      { id: "create-ticket-v3", label: "v3", updatedAt: "2026-02-14" },
      { id: "create-ticket-v2", label: "v2", updatedAt: "2026-02-11" },
      { id: "create-ticket-v1", label: "v1", updatedAt: "2026-02-04" },
    ],
  },
  {
    id: "email-response-bot",
    name: "Email Response Bot",
    versions: [
      { id: "email-response-bot-v1", label: "v1", updatedAt: "2026-02-09" },
    ],
  },
  {
    id: "customer-onboarding-assistant",
    name: "Customer Onboarding Assistant",
    versions: [
      {
        id: "customer-onboarding-assistant-v1",
        label: "v1",
        updatedAt: "2026-02-12",
      },
    ],
  },
  {
    id: "refund-resolution-agent",
    name: "Refund Resolution Agent",
    versions: [
      {
        id: "refund-resolution-agent-v1",
        label: "v1",
        updatedAt: "2026-02-13",
      },
    ],
  },
  {
    id: "meeting-brief-generator",
    name: "Meeting Brief Generator",
    versions: [
      {
        id: "meeting-brief-generator-v1",
        label: "v1",
        updatedAt: "2026-02-14",
      },
    ],
  },
  {
    id: "nps-feedback-analyzer",
    name: "NPS Feedback Analyzer",
    versions: [
      {
        id: "nps-feedback-analyzer-v1",
        label: "v1",
        updatedAt: "2026-02-07",
      },
    ],
  },
  {
    id: "renewal-copilot",
    name: "Renewal Copilot",
    versions: [
      { id: "renewal-copilot-v1", label: "v1", updatedAt: "2026-02-11" },
    ],
  },
  {
    id: "bug-triage-assistant",
    name: "Bug Triage Assistant",
    versions: [
      {
        id: "bug-triage-assistant-v1",
        label: "v1",
        updatedAt: "2026-02-05",
      },
    ],
  },
];

export const StepAttachFlows = ({
  selectedItems,
  toggleItem,
  flows,
}: StepAttachFlowsProps) => {
  void selectedItems;
  void toggleItem;
  void flows;

  const [selectedFlowId, setSelectedFlowId] = useState<string>(
    MOCK_FLOW_ITEMS[0]?.id ?? "",
  );
  const [selectedVersionId, setSelectedVersionId] = useState<string>(
    MOCK_FLOW_ITEMS[0]?.attachedVersionId ?? "",
  );

  const selectedFlow = useMemo(
    () => MOCK_FLOW_ITEMS.find((flow) => flow.id === selectedFlowId),
    [selectedFlowId],
  );

  useEffect(() => {
    if (!selectedFlow) return;
    setSelectedVersionId(
      selectedFlow.attachedVersionId ?? selectedFlow.versions[0]?.id ?? "",
    );
  }, [selectedFlow]);

  const canAttach =
    Boolean(selectedVersionId) &&
    selectedVersionId !== selectedFlow?.attachedVersionId;

  return (
    <div className="h-full w-full overflow-hidden rounded-xl border border-border">
      <div className="grid h-full grid-cols-[1fr_1.3fr] bg-background">
        <div className="flex min-h-0 h-full flex-col border-r border-border">
          <div className="border-b border-border p-4 text-sm text-muted-foreground">
            Available Flows
          </div>
          <div className="relative min-h-0 flex-1">
            <div className="h-full overflow-y-auto">
              {MOCK_FLOW_ITEMS.map((flow) => {
                const isSelected = selectedFlowId === flow.id;

                return (
                  <button
                    key={flow.id}
                    type="button"
                    onClick={() => setSelectedFlowId(flow.id)}
                    className={`flex w-full items-start gap-3 p-4 text-left transition-colors ${
                      isSelected
                        ? "border-border bg-muted"
                        : "border-transparent hover:border-border hover:bg-muted/60"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-sm font-semibold">
                          {flow.name}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {flow.versions.length} version
                        {flow.versions.length === 1 ? "" : "s"}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="flex h-full min-h-0 flex-col">
          <div className="border-b border-border p-4 text-sm text-muted-foreground">
            Select a version to attach to this deployment
          </div>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden pl-4 py-2">
            <h3 className="text-[18px] py-2 font-semibold leading-tight">
              {selectedFlow?.name}
            </h3>
            <div className="relative min-h-0 flex-1">
              <div className="h-full overflow-y-auto pr-4 [mask-image:linear-gradient(to_bottom,transparent,black_14px,black_calc(100%-14px),transparent)] [-webkit-mask-image:linear-gradient(to_bottom,transparent,black_14px,black_calc(100%-14px),transparent)]">
                <div className="space-y-3 py-3">
                  {selectedFlow?.versions.map((version) => {
                    const isSelected = selectedVersionId === version.id;

                    return (
                      <button
                        key={version.id}
                        type="button"
                        onClick={() => setSelectedVersionId(version.id)}
                        className={`flex w-full items-center gap-4 rounded-xl border p-3 text-left transition-colors ${
                          isSelected
                            ? "border-primary bg-primary/10"
                            : "border-transparent bg-muted hover:border-border"
                        }`}
                      >
                        <Checkbox
                          checked={isSelected}
                          className="pointer-events-none"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium leading-none">
                              {version.label}
                            </span>
                          </div>
                          <p className="pt-1 text-xs text-muted-foreground">
                            Last updated: {version.updatedAt}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="mt-auto py-2 pr-4">
              <Button type="button" className="w-full" disabled={!canAttach}>
                Attach Flow
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
