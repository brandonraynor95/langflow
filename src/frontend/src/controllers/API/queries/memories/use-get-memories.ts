import type { UseQueryResult } from "@tanstack/react-query";
import type { useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";
import {
  isMockMemoriesEnabled,
  mockMemoriesApi,
  type MemoryInfo,
} from "../../mocks/memories";

export type { MemoryInfo };

interface GetMemoriesParams {
  flowId?: string;
}

export const useGetMemories: useQueryFunctionType<
  GetMemoriesParams,
  MemoryInfo[]
> = (params, options?) => {
  const { query } = UseRequestProcessor();

  const getMemoriesFn = async (): Promise<MemoryInfo[]> => {
    if (isMockMemoriesEnabled()) {
      return await mockMemoriesApi.list(params?.flowId);
    }

    const url = params?.flowId
      ? `${getURL("MEMORIES")}/?flow_id=${params.flowId}`
      : `${getURL("MEMORIES")}/`;
    const res = await api.get(url);
    return res.data;
  };

  const queryResult: UseQueryResult<MemoryInfo[], any> = query(
    ["useGetMemories", params?.flowId],
    getMemoriesFn,
    {
      refetchOnWindowFocus: false,
      ...options,
    },
  );

  return queryResult;
};
