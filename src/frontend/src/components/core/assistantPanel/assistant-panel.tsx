import { useCallback, useEffect, useRef, useState } from "react";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import type { AgenticStepType } from "@/controllers/API/queries/agentic";
import { cn } from "@/utils/utils";
import type {
  AssistantModel,
  AssistantPanelProps,
} from "./assistant-panel.types";
import { AssistantHeader } from "./components/assistant-header";
import { AssistantInput } from "./components/assistant-input";
import { AssistantMessageItem } from "./components/assistant-message";
import { AssistantNoModelsState } from "./components/assistant-no-models-state";
import { useAssistantChat, useEnabledModels } from "./hooks";

const PANEL_SIZE_KEY = "langflow-assistant-panel-size";
const DEFAULT_SIZE = { width: 620, height: 600 };
const MIN_SIZE = { width: 400, height: 400 };
const MAX_SIZE = { width: 900, height: 800 };

function getStoredSize(): { width: number; height: number } {
  try {
    const stored = localStorage.getItem(PANEL_SIZE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed.width && parsed.height) return parsed;
    }
  } catch {
    // ignore
  }
  return DEFAULT_SIZE;
}

interface AssistantInputWithScrollProps {
  onSend: (content: string, model: AssistantModel | null) => void;
  onStop: () => void;
  disabled: boolean;
  isProcessing: boolean;
  currentStep: AgenticStepType | null;
  autoFocus?: boolean;
}

function AssistantInputWithScroll({
  onSend,
  onStop,
  disabled,
  isProcessing,
  currentStep,
  autoFocus,
}: AssistantInputWithScrollProps) {
  const { scrollToBottom } = useStickToBottomContext();

  const handleSend = (content: string, model: AssistantModel | null) => {
    scrollToBottom({ animation: "smooth", duration: 300 });
    onSend(content, model);
  };

  return (
    <AssistantInput
      onSend={handleSend}
      onStop={onStop}
      disabled={disabled}
      isProcessing={isProcessing}
      currentStep={currentStep}
      autoFocus={autoFocus}
      compact
    />
  );
}

export function AssistantPanel({ isOpen, onClose }: AssistantPanelProps) {
  const { hasEnabledModels } = useEnabledModels();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: PointerEvent) => {
      const target = e.target as Node;
      // Don't close if clicking inside the panel
      if (panelRef.current && panelRef.current.contains(target)) return;
      // Don't close if clicking inside a dropdown portal, popover, or dialog
      const el = e.target as HTMLElement;
      if (
        el.closest?.("[role='menu']") ||
        el.closest?.("[data-radix-popper-content-wrapper]")
      )
        return;
      if (
        el.closest?.("[role='dialog']") ||
        el.closest?.("[data-radix-dialog-overlay]")
      )
        return;
      // Don't close if any panel dropdown or dialog is currently open (portals render outside panelRef)
      if (document.querySelector("[data-radix-popper-content-wrapper]")) return;
      if (document.querySelector("[role='dialog']")) return;
      // Don't close if clicking the canvas controls (let the toggle button handle it)
      if (el.closest?.("[data-testid='main_canvas_controls']")) return;
      // Don't close if interacting with a resize handle
      if (el.closest?.("[data-resize-handle]")) return;
      onClose();
    };

    document.addEventListener("pointerdown", handleClickOutside, true);
    return () =>
      document.removeEventListener("pointerdown", handleClickOutside, true);
  }, [isOpen, onClose]);
  const {
    messages,
    isProcessing,
    currentStep,
    handleSend,
    handleApprove,
    handleStopGeneration,
    handleClearHistory,
  } = useAssistantChat();

  const handleApproveAndClose = (messageId: string) => {
    handleApprove(messageId);
    onClose();
  };

  const hasMessages = messages.length > 0;
  const [hasExpandedOnce, setHasExpandedOnce] = useState(false);

  // Track if panel has ever shown messages (to keep expanded size after new session)
  useEffect(() => {
    if (hasMessages) setHasExpandedOnce(true);
  }, [hasMessages]);

  // Reset when panel is closed
  useEffect(() => {
    if (!isOpen) setHasExpandedOnce(false);
  }, [isOpen]);

  const useExpandedSize = hasMessages || hasExpandedOnce;
  const [panelSize, setPanelSize] = useState(getStoredSize);

  const handleEdgeResize = useCallback(
    (e: React.MouseEvent, edges: { x?: "left" | "right"; y?: "top" }) => {
      e.preventDefault();
      e.stopPropagation();
      const startX = e.clientX;
      const startY = e.clientY;
      const startW = panelSize.width;
      const startH = panelSize.height;

      const handleMouseMove = (ev: MouseEvent) => {
        let newW = startW;
        let newH = startH;

        if (edges.x === "right") {
          newW = startW + (ev.clientX - startX);
        } else if (edges.x === "left") {
          newW = startW - (ev.clientX - startX);
        }

        if (edges.y === "top") {
          newH = startH - (ev.clientY - startY);
        }

        setPanelSize({
          width: Math.min(MAX_SIZE.width, Math.max(MIN_SIZE.width, newW)),
          height: Math.min(MAX_SIZE.height, Math.max(MIN_SIZE.height, newH)),
        });
      };

      const handleMouseUp = () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        setPanelSize((prev) => {
          localStorage.setItem(PANEL_SIZE_KEY, JSON.stringify(prev));
          return prev;
        });
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [panelSize],
  );

  const containerClasses = cn(
    "flex flex-col transition-[opacity,transform] duration-200 fixed shadow-xl will-change-[opacity,transform]",
    "z-50 bottom-16 left-[calc(50%+140px)] -translate-x-1/2 rounded-2xl border border-border",
    isOpen
      ? "opacity-100 translate-y-0"
      : "opacity-0 translate-y-4 pointer-events-none",
  );

  const containerStyle = useExpandedSize
    ? {
        width: panelSize.width,
        height: panelSize.height,
      }
    : {
        width: panelSize.width,
      };

  return (
    <div ref={panelRef} className={containerClasses} style={containerStyle}>
      <div className="absolute inset-0 rounded-2xl bg-background" />

      <div className="relative z-10 flex h-full min-h-0 flex-col overflow-hidden">
        <AssistantHeader
          onClose={onClose}
          onNewSession={handleClearHistory}
          hasMessages={hasMessages}
        />
        {!hasEnabledModels ? (
          <>
            <div className="flex flex-1 flex-col overflow-hidden">
              <AssistantNoModelsState />
            </div>
            <AssistantInput
              onSend={handleSend}
              disabled={true}
              placeholder="Configure Model Providers..."
            />
          </>
        ) : hasMessages ? (
          <StickToBottom
            className="flex flex-1 flex-col overflow-hidden"
            resize="smooth"
            initial="instant"
          >
            <StickToBottom.Content className="flex min-h-full flex-col justify-end px-4 pt-4 pb-0">
              {messages.map((msg) => (
                <AssistantMessageItem
                  key={msg.id}
                  message={msg}
                  onApprove={handleApproveAndClose}
                />
              ))}
            </StickToBottom.Content>
            <AssistantInputWithScroll
              onSend={handleSend}
              onStop={handleStopGeneration}
              disabled={isProcessing}
              isProcessing={isProcessing}
              currentStep={currentStep}
              autoFocus={isOpen}
            />
          </StickToBottom>
        ) : (
          <AssistantInput
            onSend={handleSend}
            onStop={handleStopGeneration}
            disabled={false}
            isProcessing={isProcessing}
            currentStep={currentStep}
            compact={hasExpandedOnce}
            autoFocus={isOpen}
          />
        )}
      </div>

      {/* Edge resize handles — invisible hitboxes with hover highlight */}
      {useExpandedSize && (
        <>
          {/* Left edge */}
          <div
            data-resize-handle
            className="absolute top-3 bottom-3 -left-[5px] z-30 w-[10px] cursor-ew-resize rounded-full transition-colors hover:bg-primary/20"
            onMouseDown={(e) => handleEdgeResize(e, { x: "left" })}
          />
          {/* Right edge */}
          <div
            data-resize-handle
            className="absolute top-3 bottom-3 -right-[5px] z-30 w-[10px] cursor-ew-resize rounded-full transition-colors hover:bg-primary/20"
            onMouseDown={(e) => handleEdgeResize(e, { x: "right" })}
          />
          {/* Top edge */}
          <div
            data-resize-handle
            className="absolute -top-[5px] right-3 left-3 z-30 h-[10px] cursor-ns-resize rounded-full transition-colors hover:bg-primary/20"
            onMouseDown={(e) => handleEdgeResize(e, { y: "top" })}
          />
          {/* Top-left corner */}
          <div
            data-resize-handle
            className="absolute -top-[5px] -left-[5px] z-30 h-[14px] w-[14px] cursor-nw-resize rounded-full transition-colors hover:bg-primary/30"
            onMouseDown={(e) => handleEdgeResize(e, { x: "left", y: "top" })}
          />
          {/* Top-right corner */}
          <div
            data-resize-handle
            className="absolute -top-[5px] -right-[5px] z-30 h-[14px] w-[14px] cursor-ne-resize rounded-full transition-colors hover:bg-primary/30"
            onMouseDown={(e) => handleEdgeResize(e, { x: "right", y: "top" })}
          />
        </>
      )}
    </div>
  );
}

export default AssistantPanel;
