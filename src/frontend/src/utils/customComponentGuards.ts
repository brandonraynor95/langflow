import useFlowStore from "@/stores/flowStore";
import { useTypesStore } from "@/stores/typesStore";

/**
 * Checks whether a node is outdated (stale code) and should be skipped
 * for API calls when custom components are not allowed.
 *
 * Two-layer check:
 * 1. Fast path via componentsToUpdate state
 * 2. Direct code comparison against templates (covers race where
 *    componentsToUpdate hasn't been populated yet)
 */
export function isNodeOutdated(
  nodeId: string,
  currentCodeValue?: string,
): boolean {
  // Fast path: check componentsToUpdate
  const componentsToUpdate = useFlowStore.getState().componentsToUpdate;
  const outdatedEntry = componentsToUpdate.some(
    (c) => c.id === nodeId && c.outdated && !c.userEdited,
  );
  if (outdatedEntry) return true;

  // Slow path: compare code against server templates
  const nodeType = useFlowStore.getState().getNode(nodeId)?.data?.type;
  if (nodeType && currentCodeValue !== undefined) {
    const templates = useTypesStore.getState().templates;
    const serverCode = templates[nodeType]?.template?.code?.value;
    if (serverCode && serverCode !== currentCodeValue) {
      return true;
    }
  }

  return false;
}

/**
 * Checks whether an API error is a 403 specifically from the backend
 * blocking a custom component (not an unrelated auth/permission error).
 */
// biome-ignore lint/suspicious/noExplicitAny: error objects have dynamic shape from axios
export function isCustomComponentBlockError(error: any): boolean {
  const e = error;
  return (
    e?.response?.status === 403 &&
    typeof e?.response?.data?.detail === "string" &&
    e.response.data.detail.includes("Custom component")
  );
}
