import { useStoreApi } from "@xyflow/react";
import { cloneDeep } from "lodash";
import { useCallback } from "react";
import { NODE_WIDTH } from "@/constants/constants";
import { track } from "@/customization/utils/analytics";
import { useCloudModeStore } from "@/stores/cloudModeStore";
import useFlowStore from "@/stores/flowStore";
import type { APIClassType } from "@/types/api";
import type { AllNodeType } from "@/types/flow";
import { getNodeId } from "@/utils/reactflowUtils";
import { getNodeRenderType } from "@/utils/utils";

type CloudFieldOverride = {
  value?: unknown;
  placeholder?: string;
};

type CloudComponentMetadata = {
  cloud_default_overrides?: Record<string, CloudFieldOverride>;
  cloud_incompatible_options?: Record<string, unknown[]>;
};

const getOptionName = (option: unknown) => {
  if (typeof option === "object" && option !== null && "name" in option) {
    return (option as { name?: unknown }).name;
  }

  return option;
};

const sanitizeCloudIncompatibleDefaults = (
  component: APIClassType,
  cloudIncompatibleOptions?: Record<string, unknown[]>,
) => {
  if (!cloudIncompatibleOptions) {
    return;
  }

  Object.entries(cloudIncompatibleOptions).forEach(
    ([fieldName, incompatibleOptions]) => {
      if (!Array.isArray(incompatibleOptions)) {
        return;
      }

      const templateField = component.template?.[fieldName];
      if (!templateField) {
        return;
      }

      const selectedOptions = Array.isArray(templateField.value)
        ? templateField.value
        : templateField.value
          ? [templateField.value]
          : [];

      const filteredSelections = selectedOptions.filter(
        (selection) => !incompatibleOptions.includes(getOptionName(selection)),
      );

      if (filteredSelections.length > 0) {
        templateField.value = filteredSelections;
        return;
      }

      if (templateField.limit !== 1 || !Array.isArray(templateField.options)) {
        templateField.value = filteredSelections;
        return;
      }

      const firstCompatibleOption = templateField.options.find(
        (option) => !incompatibleOptions.includes(getOptionName(option)),
      );

      templateField.value = firstCompatibleOption
        ? [cloneDeep(firstCompatibleOption)]
        : [];
    },
  );
};

export function useAddComponent() {
  const store = useStoreApi();
  const paste = useFlowStore((state) => state.paste);
  const filterEdge = useFlowStore((state) => state.getFilterEdge);
  const filterType = useFlowStore((state) => state.filterType);
  const cloudOnly = useCloudModeStore((state) => state.cloudOnly);

  const addComponent = useCallback(
    (
      component: APIClassType,
      type: string,
      position?: { x: number; y: number },
    ) => {
      track("Component Added", { componentType: component.display_name });

      const {
        height,
        width,
        transform: [transformX, transformY, zoomLevel],
      } = store.getState();

      const zoomMultiplier = 1 / zoomLevel;

      let pos;

      if (position) {
        pos = position;
      } else {
        let centerX, centerY;

        centerX = -transformX * zoomMultiplier + (width * zoomMultiplier) / 2;
        centerY = -transformY * zoomMultiplier + (height * zoomMultiplier) / 2;

        const nodeOffset = NODE_WIDTH / 2;

        pos = {
          x: -nodeOffset,
          y: -nodeOffset,
          paneX: centerX,
          paneY: centerY,
        };
      }

      const newId = getNodeId(type);

      const outputType = filterType?.type;

      const outputToFilter = component.outputs?.find(
        (output) => outputType && output.types.includes(outputType),
      );

      const componentMetadata = component.metadata as
        | CloudComponentMetadata
        | undefined;

      const cloudDefaultOverrides = componentMetadata?.cloud_default_overrides;
      const cloudIncompatibleOptions =
        componentMetadata?.cloud_incompatible_options;

      const componentNode =
        cloudOnly && (cloudDefaultOverrides || cloudIncompatibleOptions)
          ? (() => {
              const clonedComponent = cloneDeep(component);

              if (cloudDefaultOverrides) {
                Object.entries(cloudDefaultOverrides).forEach(
                  ([fieldName, override]) => {
                    if (!clonedComponent.template?.[fieldName]) {
                      return;
                    }

                    if (Object.hasOwn(override, "value")) {
                      clonedComponent.template[fieldName].value =
                        override.value;
                    }

                    if (override.placeholder !== undefined) {
                      clonedComponent.template[fieldName].placeholder =
                        override.placeholder;
                    }
                  },
                );
              }

              sanitizeCloudIncompatibleDefaults(
                clonedComponent,
                cloudIncompatibleOptions,
              );

              return clonedComponent;
            })()
          : component;

      const newNode: AllNodeType = {
        id: newId,
        type: getNodeRenderType("genericnode"),
        position: { x: 0, y: 0 },
        data: {
          node: componentNode,
          showNode: !componentNode.minimized,
          type: type,
          id: newId,
          ...(outputToFilter && { selected_output: outputToFilter.name }),
        },
      };

      paste({ nodes: [newNode], edges: [] }, pos);
    },
    [store, paste, filterEdge, cloudOnly],
  );

  return addComponent;
}
