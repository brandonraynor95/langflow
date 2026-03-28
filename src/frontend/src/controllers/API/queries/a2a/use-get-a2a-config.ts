import { useQuery } from "@tanstack/react-query";
import { api } from "../../api";

export type A2AConfig = {
  a2a_enabled: boolean;
  a2a_agent_slug: string | null;
  a2a_name: string | null;
  a2a_description: string | null;
  a2a_input_mode: string;
  a2a_output_mode: string;
};

export const useGetA2AConfig = (flowId: string, enabled = true) => {
  return useQuery<A2AConfig>({
    queryKey: ["a2aConfig", flowId],
    queryFn: async () => {
      const { data } = await api.get<A2AConfig>(
        `/api/v1/flows/${flowId}/a2a-config`,
      );
      return data;
    },
    enabled: enabled && !!flowId,
  });
};
