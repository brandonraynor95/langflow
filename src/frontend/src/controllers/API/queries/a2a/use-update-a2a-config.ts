import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api";
import type { A2AConfig } from "./use-get-a2a-config";

export type A2AConfigUpdate = {
  a2a_enabled?: boolean;
  a2a_agent_slug?: string;
  a2a_name?: string;
  a2a_description?: string;
};

export const useUpdateA2AConfig = (flowId: string) => {
  const queryClient = useQueryClient();

  return useMutation<A2AConfig, Error, A2AConfigUpdate>({
    mutationFn: async (config: A2AConfigUpdate) => {
      const { data } = await api.put<A2AConfig>(
        `/api/v1/flows/${flowId}/a2a-config`,
        config,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["a2aConfig", flowId] });
      queryClient.invalidateQueries({ queryKey: ["a2aFlows"] });
    },
  });
};
