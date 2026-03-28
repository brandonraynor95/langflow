import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ForwardedIconComponent } from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { api } from "@/controllers/API/api";
import useAlertStore from "@/stores/alertStore";
import { useFolderStore } from "@/stores/foldersStore";

type FlowA2AState = {
  id: string;
  name: string;
  description: string | null;
  a2a_enabled: boolean;
  a2a_agent_slug: string;
  saving: boolean;
  dirty: boolean;
};

const A2AServerTab = ({ folderName }: { folderName: string }) => {
  const { folderId } = useParams();
  const myCollectionId = useFolderStore((state) => state.myCollectionId);
  const projectId = folderId ?? myCollectionId ?? "";
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const queryClient = useQueryClient();

  const [flows, setFlows] = useState<FlowA2AState[]>([]);

  // Fetch all flows in this project
  const { data: folderData, isLoading } = useQuery({
    queryKey: ["useGetFolder", { id: projectId }],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/folders/${projectId}`);
      return data;
    },
    enabled: !!projectId,
  });

  // Initialize flow state from folder data
  useEffect(() => {
    if (!folderData?.flows) return;
    setFlows(
      folderData.flows
        .filter((f: any) => !f.is_component)
        .map((f: any) => ({
          id: f.id,
          name: f.name,
          description: f.description,
          a2a_enabled: f.a2a_enabled ?? false,
          a2a_agent_slug: f.a2a_agent_slug ?? "",
          saving: false,
          dirty: false,
        })),
    );
  }, [folderData]);

  const handleToggle = useCallback(
    async (flowId: string, enabled: boolean) => {
      const flow = flows.find((f) => f.id === flowId);
      if (!flow) return;

      // If enabling and no slug, auto-generate from name
      const slug =
        flow.a2a_agent_slug ||
        flow.name
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, "")
          .slice(0, 64);

      if (enabled && slug.length < 3) {
        setErrorData({
          title: "Invalid slug",
          list: ["Agent slug must be at least 3 characters"],
        });
        return;
      }

      setFlows((prev) =>
        prev.map((f) =>
          f.id === flowId ? { ...f, saving: true } : f,
        ),
      );

      try {
        await api.put(`/api/v1/flows/${flowId}/a2a-config`, {
          a2a_enabled: enabled,
          a2a_agent_slug: slug,
        });
        setFlows((prev) =>
          prev.map((f) =>
            f.id === flowId
              ? { ...f, a2a_enabled: enabled, a2a_agent_slug: slug, saving: false, dirty: false }
              : f,
          ),
        );
        queryClient.invalidateQueries({ queryKey: ["useGetFolder"] });
        setSuccessData({
          title: enabled
            ? `A2A enabled for "${flow.name}" at /a2a/${slug}/`
            : `A2A disabled for "${flow.name}"`,
        });
      } catch (error: any) {
        const detail = error?.response?.data?.detail || "Failed to update A2A config";
        setErrorData({ title: "A2A config error", list: [detail] });
        setFlows((prev) =>
          prev.map((f) =>
            f.id === flowId ? { ...f, saving: false } : f,
          ),
        );
      }
    },
    [flows, setSuccessData, setErrorData, queryClient],
  );

  const handleSlugChange = useCallback((flowId: string, slug: string) => {
    setFlows((prev) =>
      prev.map((f) =>
        f.id === flowId ? { ...f, a2a_agent_slug: slug, dirty: true } : f,
      ),
    );
  }, []);

  const handleSlugSave = useCallback(
    async (flowId: string) => {
      const flow = flows.find((f) => f.id === flowId);
      if (!flow || !flow.dirty) return;

      setFlows((prev) =>
        prev.map((f) => (f.id === flowId ? { ...f, saving: true } : f)),
      );

      try {
        await api.put(`/api/v1/flows/${flowId}/a2a-config`, {
          a2a_agent_slug: flow.a2a_agent_slug,
        });
        setFlows((prev) =>
          prev.map((f) =>
            f.id === flowId ? { ...f, saving: false, dirty: false } : f,
          ),
        );
        queryClient.invalidateQueries({ queryKey: ["useGetFolder"] });
        setSuccessData({ title: `Slug updated to "${flow.a2a_agent_slug}"` });
      } catch (error: any) {
        const detail = error?.response?.data?.detail || "Invalid slug";
        setErrorData({ title: "Slug error", list: [detail] });
        setFlows((prev) =>
          prev.map((f) => (f.id === flowId ? { ...f, saving: false } : f)),
        );
      }
    },
    [flows, setSuccessData, setErrorData, queryClient],
  );

  const enabledCount = flows.filter((f) => f.a2a_enabled).length;

  return (
    <div>
      <div className="flex justify-between gap-4 items-start">
        <div>
          <div className="pb-2 font-medium" data-testid="a2a-server-title">
            A2A Agents
          </div>
          <div className="pb-4 text-mmd text-muted-foreground">
            Expose your flows as A2A-compatible agents that can be discovered
            and called by external agent systems.
            {enabledCount > 0 && (
              <span className="ml-1 font-medium text-foreground">
                {enabledCount} flow{enabledCount !== 1 ? "s" : ""} exposed.
              </span>
            )}
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-mmd text-muted-foreground py-8 text-center">
          Loading flows...
        </div>
      ) : flows.length === 0 ? (
        <div className="text-mmd text-muted-foreground py-8 text-center">
          No flows in this project. Create a flow first, then come back to
          expose it as an A2A agent.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {/* Header */}
          <div className="grid grid-cols-[1fr_1fr_auto] gap-4 px-4 py-2 text-sm font-medium text-muted-foreground border-b border-border">
            <div>Flow</div>
            <div>Agent Slug</div>
            <div className="w-[60px] text-center">A2A</div>
          </div>

          {/* Flow rows */}
          {flows.map((flow) => (
            <div
              key={flow.id}
              className="grid grid-cols-[1fr_1fr_auto] gap-4 items-center px-4 py-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
              data-testid={`a2a-flow-row-${flow.id}`}
            >
              {/* Flow name + description */}
              <div className="min-w-0">
                <div className="font-medium text-sm truncate">{flow.name}</div>
                {flow.description && (
                  <div className="text-xs text-muted-foreground truncate">
                    {flow.description}
                  </div>
                )}
                {flow.a2a_enabled && flow.a2a_agent_slug && (
                  <div className="text-xs text-muted-foreground mt-0.5 font-mono">
                    /a2a/{flow.a2a_agent_slug}/.well-known/agent-card.json
                  </div>
                )}
              </div>

              {/* Slug input */}
              <div className="flex gap-2 items-center min-w-0">
                <Input
                  value={flow.a2a_agent_slug}
                  onChange={(e) =>
                    handleSlugChange(flow.id, e.target.value)
                  }
                  onBlur={() => handleSlugSave(flow.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSlugSave(flow.id);
                  }}
                  placeholder="agent-slug"
                  className="font-mono text-sm h-8"
                  disabled={flow.saving}
                  data-testid={`a2a-slug-input-${flow.id}`}
                />
              </div>

              {/* Toggle */}
              <div className="w-[60px] flex justify-center">
                <Switch
                  checked={flow.a2a_enabled}
                  onCheckedChange={(checked) =>
                    handleToggle(flow.id, checked)
                  }
                  disabled={flow.saving}
                  data-testid={`a2a-toggle-${flow.id}`}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default A2AServerTab;
