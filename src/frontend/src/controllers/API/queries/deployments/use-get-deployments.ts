import { MOCK_DEPLOYMENTS } from "@/pages/MainPage/pages/deploymentsPage/mock-data";
import type { Deployment } from "@/pages/MainPage/pages/deploymentsPage/types";
import type { useQueryFunctionType } from "@/types/api";
import { UseRequestProcessor } from "../../services/request-processor";

export interface DeploymentListResponse {
  deployments: Deployment[];
  page: number;
  size: number;
  total: number;
}

interface GetDeploymentsParams {
  provider_id: string;
  page?: number;
  size?: number;
}

export const useGetDeployments: useQueryFunctionType<
  GetDeploymentsParams,
  DeploymentListResponse
> = ({ provider_id, page = 1, size = 20 }, options) => {
  const { query } = UseRequestProcessor();

  const getDeploymentsFn = async (): Promise<DeploymentListResponse> => {
    // TODO: replace with real API call
    // const { data } = await api.get<DeploymentListResponse>(
    //   `${getURL("DEPLOYMENTS")}`,
    //   { params: { provider_id, page, size } },
    // );
    // return data;
    return {
      deployments: MOCK_DEPLOYMENTS,
      page,
      size,
      total: MOCK_DEPLOYMENTS.length,
    };
  };

  return query(
    ["useGetDeployments", { provider_id, page, size }],
    getDeploymentsFn,
    options,
  );
};
