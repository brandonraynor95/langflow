import type { UseMutationResult } from "@tanstack/react-query";
import type { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";
import {
  isMockMemoriesEnabled,
  mockMemoriesApi,
  type CreateMemoryPayload,
  type MemoryInfo,
} from "../../mocks/memories";

export interface CreateMemoryParams extends CreateMemoryPayload {}

export const useCreateMemory: useMutationFunctionType<
  undefined,
  CreateMemoryParams
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createMemoryFn = async (params: CreateMemoryParams): Promise<MemoryInfo> => {
    const response = isMockMemoriesEnabled()
      ? { data: await mockMemoriesApi.create(params) }
      : await api.post<MemoryInfo>(`${getURL("MEMORIES")}/`, params);

    queryClient.invalidateQueries({ queryKey: ["useGetMemories"] });
    return response.data;
  };

  const mutation: UseMutationResult<MemoryInfo, any, CreateMemoryParams> = mutate(
    ["useCreateMemory"],
    createMemoryFn,
    options,
  );

  return mutation;
};
