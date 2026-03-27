import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import LoadingTextComponent from "@/components/common/loadingTextComponent";
import { CLOUD_INCOMPATIBLE_PROVIDERS } from "@/constants/cloud-incompatible-providers";
import { useGetEnabledModels } from "@/controllers/API/queries/models/use-get-enabled-models";
import { useGetModelProviders } from "@/controllers/API/queries/models/use-get-model-providers";
import { useRefreshModelInputs } from "@/hooks/use-refresh-model-inputs";
import ModelProviderModal from "@/modals/modelProviderModal";
import { useCloudModeStore } from "@/stores/cloudModeStore";
import ForwardedIconComponent from "../../../../common/genericIconComponent";
import { Button } from "../../../../ui/button";
import { Command } from "../../../../ui/command";
import {
  Popover,
  PopoverContent,
  PopoverContentWithoutPortal,
} from "../../../../ui/popover";
import type { BaseInputProps } from "../../types";
import ModelList from "./components/ModelList";
import ModelTrigger from "./components/ModelTrigger";
import type { ModelInputComponentType, ModelOption } from "./types";

type ModelInputValue =
  | Array<{
      id?: string;
      name: string;
      icon?: string;
      provider?: string;
      metadata?: Record<string, unknown>;
    }>
  | "connect_other_models";

export default function ModelInputComponent({
  id,
  value,
  disabled,
  handleOnNewValue,
  options = [],
  placeholder = "Setup Provider",
  nodeId,
  nodeClass,
  handleNodeClass,
  externalOptions,
  showParameter = true,
  editNode,
  inspectionPanel,
  showEmptyState = false,
}: BaseInputProps<ModelInputValue> &
  ModelInputComponentType): JSX.Element | null {
  const refButton = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [openManageProvidersDialog, setOpenManageProvidersDialog] =
    useState(false);
  const [isRefreshingAfterClose, setIsRefreshingAfterClose] = useState(false);
  const [refreshOptions, setRefreshOptions] = useState(false);
  const { refreshAllModelInputs } = useRefreshModelInputs();

  // Ref to track if we've already processed the empty options state
  // prevents infinite loop when no models are available
  const hasProcessedEmptyRef = useRef(false);

  const modelType =
    nodeClass?.template?.model?.model_type === "language"
      ? "llm"
      : "embeddings";

  const { data: providersData = [], isFetching: isFetchingProviders } =
    useGetModelProviders({});
  const { data: enabledModelsData } = useGetEnabledModels();

  const hasEnabledProviders = useMemo(() => {
    return providersData?.some(
      (provider) => provider.is_enabled || provider.is_configured,
    );
  }, [providersData]);

  const cloudOnly = useCloudModeStore((state) => state.cloudOnly);

  const enabledOptions = useMemo(
    () =>
      options.filter((option) => {
        if (option.metadata?.is_disabled_provider) {
          return false;
        }

        const provider = option.provider || "Unknown";
        const providerModels = enabledModelsData?.enabled_models?.[provider];

        return providerModels?.[option.name] !== false;
      }),
    [enabledModelsData?.enabled_models, options],
  );

  // Groups models by their provider name for sectioned display in dropdown.
  // Filters out cloud-incompatible providers when cloud mode is active.
  const groupedOptions = useMemo(() => {
    const grouped: Record<string, ModelOption[]> = {};
    for (const option of enabledOptions) {
      const provider = option.provider || "Unknown";

      if (cloudOnly && CLOUD_INCOMPATIBLE_PROVIDERS.has(provider)) {
        continue;
      }

      if (!grouped[provider]) {
        grouped[provider] = [];
      }

      grouped[provider].push(option);
    }
    return grouped;
  }, [enabledOptions, cloudOnly]);

  // Flattened array of all enabled options for efficient lookups by name
  const flatOptions = useMemo(
    () => Object.values(groupedOptions).flat(),
    [groupedOptions],
  );

  // Derive the currently selected model from the value prop
  const selectedModel = useMemo(() => {
    // If we're in connection mode, we don't have a normal selected model
    if (value === "connect_other_models") {
      return null;
    }

    const currentValue = Array.isArray(value) ? value[0] : null;
    const currentName = currentValue?.name;
    if (!currentName) {
      // Logic to auto-select the first model if none is selected
      // We only do this check if we have options available
      if (flatOptions.length > 0 && !hasProcessedEmptyRef.current) {
        // If we haven't processed empty state yet, we render the first one
        return flatOptions[0];
      }
      return null;
    }

    const matchedOption = flatOptions.find(
      (option) => option.name === currentName,
    );

    if (matchedOption) {
      return matchedOption;
    }

    if (currentValue) {
      return {
        id: currentValue.id,
        name: currentValue.name,
        icon: currentValue.icon || "Bot",
        provider: currentValue.provider || "Unknown",
        metadata: currentValue.metadata ?? {},
      };
    }

    return flatOptions.length > 0 ? flatOptions[0] : null;
  }, [value, flatOptions]);

  const showCloudIncompatibleWarning = useMemo(
    () =>
      cloudOnly &&
      !!selectedModel?.provider &&
      CLOUD_INCOMPATIBLE_PROVIDERS.has(selectedModel.provider),
    [cloudOnly, selectedModel?.provider],
  );

  const cloudFilteredOptionCount = useMemo(
    () =>
      cloudOnly
        ? enabledOptions.filter((option) =>
            CLOUD_INCOMPATIBLE_PROVIDERS.has(option.provider || "Unknown"),
          ).length
        : 0,
    [cloudOnly, enabledOptions],
  );

  const showNoCompatibleCloudModels = useMemo(
    () =>
      cloudOnly &&
      enabledOptions.length > 0 &&
      flatOptions.length === 0 &&
      cloudFilteredOptionCount > 0 &&
      !selectedModel,
    [
      cloudFilteredOptionCount,
      cloudOnly,
      enabledOptions.length,
      flatOptions.length,
      selectedModel,
    ],
  );

  const effectiveShowEmptyState = showEmptyState || showNoCompatibleCloudModels;
  const emptyStateLabel = showNoCompatibleCloudModels
    ? "No cloud-compatible models"
    : "No models enabled";

  // Reset the ref when the available options change (e.g., cloud mode toggled)
  // so auto-select can fire again for the new option set.
  const prevFlatOptionsRef = useRef(flatOptions);
  if (prevFlatOptionsRef.current !== flatOptions) {
    prevFlatOptionsRef.current = flatOptions;
    hasProcessedEmptyRef.current = false;
  }

  useEffect(() => {
    // Only proceed if we have options and haven't selected a value
    if (flatOptions.length > 0 && (!value || value.length === 0)) {
      // Check ref to avoid infinite loops
      if (!hasProcessedEmptyRef.current) {
        const firstOption = flatOptions[0];
        // Construct the new value object
        const newValue = [
          {
            ...(firstOption.id && { id: firstOption.id }),
            name: firstOption.name,
            icon: firstOption.icon || "Bot",
            provider: firstOption.provider || "Unknown",
            metadata: firstOption.metadata ?? {},
          },
        ];
        handleOnNewValue({ value: newValue });
        hasProcessedEmptyRef.current = true;
      }
    }
  }, [flatOptions, value, handleOnNewValue]);

  /**
   * Handles model selection from the dropdown.
   */
  const handleModelSelect = useCallback(
    (modelName: string) => {
      const selectedOption = flatOptions.find(
        (option) => option.name === modelName,
      );
      if (!selectedOption) return;

      // Build normalized value - only include id if it exists
      const newValue = [
        {
          ...(selectedOption.id && { id: selectedOption.id }),
          name: selectedOption.name,
          icon: selectedOption.icon || "Bot",
          provider: selectedOption.provider || "Unknown",
          metadata: selectedOption.metadata ?? {},
        },
      ];

      handleOnNewValue({ value: newValue });
      setOpen(false);
    },
    [flatOptions, handleOnNewValue],
  );

  const handleRefreshButtonPress = useCallback(async () => {
    setOpen(false);
    setRefreshOptions(true);
    try {
      await refreshAllModelInputs({ silent: true });
    } catch (error) {
      console.error("ModelInputComponent: refresh failed", error);
    } finally {
      setRefreshOptions(false);
    }
  }, [refreshAllModelInputs]);

  const handleManageProvidersDialogClose = useCallback(() => {
    setOpenManageProvidersDialog(false);
    setIsRefreshingAfterClose(true);
  }, []);

  // Clear the refreshing indicator after the providers query completes a full
  // refetch cycle (isFetchingProviders: false → true → false). We track whether
  // we've seen the fetch start so we don't clear prematurely before the
  // invalidation has even been triggered by refreshAllModelInputs.
  const hasSeenFetchStartRef = useRef(false);
  useEffect(() => {
    if (!isRefreshingAfterClose) {
      hasSeenFetchStartRef.current = false;
      return;
    }
    if (isFetchingProviders) {
      hasSeenFetchStartRef.current = true;
    } else if (hasSeenFetchStartRef.current) {
      setIsRefreshingAfterClose(false);
    }
  }, [isRefreshingAfterClose, isFetchingProviders]);

  // Safety timeout: clear loading even if no refetch cycle is detected
  // (e.g. no model nodes on canvas, or the refresh was a no-op)
  useEffect(() => {
    if (!isRefreshingAfterClose) return;
    const timeout = setTimeout(() => setIsRefreshingAfterClose(false), 5000);
    return () => clearTimeout(timeout);
  }, [isRefreshingAfterClose]);

  const renderLoadingButton = () => (
    <Button
      className="dropdown-component-false-outline w-full justify-between py-2 font-normal"
      variant="primary"
      size="xs"
      disabled
    >
      <LoadingTextComponent text="Loading models" />
    </Button>
  );

  const renderFooterButton = (
    label: string,
    icon: string,
    onClick: () => void,
    testId?: string,
  ) => (
    <Button
      className="w-full flex cursor-pointer items-center justify-start gap-2 truncate py-2 text-xs text-muted-foreground px-3 hover:bg-accent group"
      unstyled
      data-testid={testId}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 pl-1 group-hover:text-primary">
        {label}
        <ForwardedIconComponent
          name={icon}
          className="w-4 h-4 text-muted-foreground group-hover:text-primary"
        />
      </div>
    </Button>
  );

  const renderManageProvidersButton = () => (
    <div className="bottom-0 bg-background">
      {renderFooterButton(
        "Manage Model Providers",
        "Settings",
        () => setOpenManageProvidersDialog(true),
        "manage-model-providers",
      )}
    </div>
  );

  const renderPopoverContent = () => {
    const PopoverContentInput =
      editNode || inspectionPanel
        ? PopoverContent
        : PopoverContentWithoutPortal;
    return (
      <PopoverContentInput
        side="bottom"
        avoidCollisions={true}
        className="noflow nowheel nopan nodelete nodrag p-0"
        style={{ minWidth: refButton?.current?.clientWidth ?? "200px" }}
      >
        <Command className="flex flex-col">
          <ModelList
            groupedOptions={groupedOptions}
            selectedModel={selectedModel}
            onSelect={handleModelSelect}
          />
          {renderFooterButton(
            "Refresh List",
            "RotateCw",
            handleRefreshButtonPress,
            "refresh-model-list",
          )}
          {renderManageProvidersButton()}
        </Command>
      </PopoverContentInput>
    );
  };

  if (!showParameter) {
    return null;
  }

  // Loading state (skip if showEmptyState is true - we want to show the empty dropdown instead)
  if (
    ((!options || options.length === 0) && !effectiveShowEmptyState) ||
    isRefreshingAfterClose ||
    refreshOptions
  ) {
    return <div className="w-full">{renderLoadingButton()}</div>;
  }

  // Main render
  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <div className="w-full truncate">
          <ModelTrigger
            open={open}
            disabled={disabled}
            visibleOptionsCount={flatOptions.length}
            selectedModel={selectedModel}
            showCloudIncompatibleWarning={showCloudIncompatibleWarning}
            placeholder={placeholder}
            hasEnabledProviders={hasEnabledProviders ?? false}
            onOpenManageProviders={() => setOpenManageProvidersDialog(true)}
            id={id}
            refButton={refButton}
            showEmptyState={effectiveShowEmptyState}
            emptyStateLabel={emptyStateLabel}
          />
        </div>
        {renderPopoverContent()}
      </Popover>

      {openManageProvidersDialog && (
        <ModelProviderModal
          open={openManageProvidersDialog}
          onClose={handleManageProvidersDialogClose}
          modelType={modelType || "llm"}
        />
      )}
    </>
  );
}
