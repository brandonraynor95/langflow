import { MOCK_PROVIDER_INSTANCES } from "@/pages/MainPage/pages/deploymentsPage/mock-data";
import type { ProviderAccount } from "@/pages/MainPage/pages/deploymentsPage/types";
import type { useQueryFunctionType } from "@/types/api";
import { UseRequestProcessor } from "../../services/request-processor";

export interface ProviderAccountListResponse {
  providers: ProviderAccount[];
  page: number;
  size: number;
  total: number;
}

interface GetProviderAccountsParams {
  page?: number;
  size?: number;
}

export const useGetProviderAccounts: useQueryFunctionType<
  GetProviderAccountsParams,
  ProviderAccountListResponse
> = ({ page = 1, size = 20 } = {}, options) => {
  const { query } = UseRequestProcessor();

  const getProviderAccountsFn =
    async (): Promise<ProviderAccountListResponse> => {
      // TODO: replace with real API call
      // const { data } = await api.get<ProviderAccountListResponse>(
      //   `${getURL("DEPLOYMENT_PROVIDER_ACCOUNTS")}`,
      //   { params: { page, size } },
      // );
      // return data;
      return {
        providers: MOCK_PROVIDER_INSTANCES,
        page,
        size,
        total: MOCK_PROVIDER_INSTANCES.length,
      };
    };

  return query(
    ["useGetProviderAccounts", { page, size }],
    getProviderAccountsFn,
    options,
  );
};
