import type { APIClassType } from "@/types/api";

type CloudFieldOverride = {
  value?: unknown;
  placeholder?: string;
};

type CloudUiMetadata = Record<string, unknown> & {
  cloud_default_overrides?: Record<string, CloudFieldOverride>;
  cloud_incompatible_options?: Record<string, unknown[]>;
};

function isCloudUiMetadata(value: unknown): value is CloudUiMetadata {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function withCurrentCloudMetadata(
  savedNode: APIClassType | undefined,
  currentCatalogNode: APIClassType | undefined,
): APIClassType | undefined {
  if (!savedNode || !currentCatalogNode) {
    return savedNode;
  }

  const savedMetadata = isCloudUiMetadata(savedNode.metadata)
    ? savedNode.metadata
    : undefined;
  const currentMetadata = isCloudUiMetadata(currentCatalogNode.metadata)
    ? currentCatalogNode.metadata
    : undefined;

  const shouldOverlayCloudCompatible =
    savedNode.cloud_compatible === undefined &&
    currentCatalogNode.cloud_compatible !== undefined;
  const shouldOverlayCloudDefaultOverrides =
    savedMetadata?.cloud_default_overrides === undefined &&
    currentMetadata?.cloud_default_overrides !== undefined;
  const shouldOverlayCloudIncompatibleOptions =
    savedMetadata?.cloud_incompatible_options === undefined &&
    currentMetadata?.cloud_incompatible_options !== undefined;

  if (
    !shouldOverlayCloudCompatible &&
    !shouldOverlayCloudDefaultOverrides &&
    !shouldOverlayCloudIncompatibleOptions
  ) {
    return savedNode;
  }

  const nextMetadata =
    shouldOverlayCloudDefaultOverrides || shouldOverlayCloudIncompatibleOptions
      ? {
          ...((savedMetadata ?? {}) as Record<string, unknown>),
          ...(shouldOverlayCloudDefaultOverrides
            ? {
                cloud_default_overrides:
                  currentMetadata?.cloud_default_overrides,
              }
            : {}),
          ...(shouldOverlayCloudIncompatibleOptions
            ? {
                cloud_incompatible_options:
                  currentMetadata?.cloud_incompatible_options,
              }
            : {}),
        }
      : savedMetadata;

  return {
    ...savedNode,
    ...(shouldOverlayCloudCompatible
      ? {
          cloud_compatible: currentCatalogNode.cloud_compatible,
        }
      : {}),
    ...(nextMetadata !== undefined
      ? {
          metadata: nextMetadata,
        }
      : {}),
  } as APIClassType;
}
