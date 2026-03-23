import { useCallback, useRef, useState } from "react";
import ShortUniqueId from "short-unique-id";
import {
  type AgenticFlowUpdateEvent,
  type AgenticStepType,
  postAssistStream,
} from "@/controllers/API/queries/agentic";
import { usePostValidateComponentCode } from "@/controllers/API/queries/nodes/use-post-validate-component-code";
import { useAddComponent } from "@/hooks/use-add-component";
import useFlowStore from "@/stores/flowStore";
import useFlowsManagerStore from "@/stores/flowsManagerStore";
import type { APIClassType } from "@/types/api";
import type {
  AssistantMessage,
  AssistantModel,
} from "../assistant-panel.types";

const uid = new ShortUniqueId();

interface UseAssistantChatReturn {
  messages: AssistantMessage[];
  isProcessing: boolean;
  currentStep: AgenticStepType | null;
  handleSend: (content: string, model: AssistantModel | null) => Promise<void>;
  handleApprove: (messageId: string) => Promise<void>;
  handleUpdateFlowAction: (
    messageId: string,
    actionId: string,
    status: "applied" | "dismissed",
  ) => void;
  handleStopGeneration: () => void;
  handleClearHistory: () => void;
}

export function useAssistantChat(): UseAssistantChatReturn {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<AgenticStepType | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string>(uid.randomUUID(16));

  const currentFlowId = useFlowsManagerStore((state) => state.currentFlowId);
  const addComponent = useAddComponent();
  const { mutateAsync: validateComponent } = usePostValidateComponentCode();
  const paste = useFlowStore((state) => state.paste);

  /** Apply a flow_update event to the canvas in real time */
  const applyFlowUpdate = useCallback(
    (event: AgenticFlowUpdateEvent) => {
      switch (event.action) {
        case "set_flow": {
          const flow = event.flow as {
            data?: { nodes?: unknown[]; edges?: unknown[] };
          };
          if (flow?.data?.nodes) {
            paste(
              {
                nodes: flow.data.nodes as never[],
                edges: (flow.data.edges ?? []) as never[],
              },
              { x: 100, y: 100 },
            );
          }
          break;
        }
        case "add_component": {
          const node = event.node as Record<string, unknown>;
          if (node) {
            // Add node at its layout position using setNodes
            const setNodes = useFlowStore.getState().setNodes;
            setNodes((prev) => [...prev, node as never]);
          }
          break;
        }
        case "connect": {
          const edge = event.edge as Record<string, unknown>;
          if (edge) {
            const setEdges = useFlowStore.getState().setEdges;
            setEdges((prev) => [...prev, edge as never]);
          }
          break;
        }
        // configure and remove_component would need different handling
        // For the spike, these are logged but not applied visually
        default:
          break;
      }
    },
    [paste],
  );

  const handleSend = useCallback(
    async (content: string, model: AssistantModel | null) => {
      if (isProcessing) return;

      if (!model?.provider || !model?.name) {
        return;
      }

      const userMessage: AssistantMessage = {
        id: uid.randomUUID(10),
        role: "user",
        content,
        timestamp: new Date(),
        status: "complete",
      };

      const assistantMessageId = uid.randomUUID(10);
      const assistantMessage: AssistantMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        status: "streaming",
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsProcessing(true);

      abortControllerRef.current = new AbortController();

      const completedSteps: AgenticStepType[] = [];

      try {
        await postAssistStream(
          {
            flow_id: currentFlowId || "",
            input_value: content,
            provider: model?.provider,
            model_name: model?.name,
            session_id: sessionIdRef.current,
          },
          {
            onProgress: (event) => {
              if (event.step !== completedSteps[completedSteps.length - 1]) {
                if (completedSteps.length > 0) {
                  completedSteps.push(
                    completedSteps[completedSteps.length - 1],
                  );
                }
              }

              setCurrentStep(event.step);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        progress: {
                          step: event.step,
                          attempt: event.attempt,
                          maxAttempts: event.max_attempts,
                          message: event.message,
                          error: event.error,
                          // Preserve componentCode and className from previous
                          // progress if the new event doesn't include them
                          className:
                            event.class_name ?? msg.progress?.className,
                          componentCode:
                            event.component_code ?? msg.progress?.componentCode,
                        },
                        completedSteps: [...completedSteps],
                      }
                    : msg,
                ),
              );
            },
            onToken: (event) => {
              setMessages((prev) =>
                prev.map((msg) => {
                  if (msg.id !== assistantMessageId) return msg;
                  // Add whitespace when tool calls break the stream:
                  // previous text ends with punctuation, new chunk starts
                  // with a word character, and there's no trailing space.
                  const prev = msg.content;
                  const chunk = event.chunk;
                  const needsSpace =
                    prev.length > 0 &&
                    /[.!?:)\]"']$/.test(prev) &&
                    /^[A-Z]/.test(chunk);
                  return {
                    ...msg,
                    content: prev + (needsSpace ? "\n\n" : "") + chunk,
                  };
                }),
              );
            },
            onFlowPreview: (event) => {
              // Apply flow to canvas immediately
              applyFlowUpdate({
                event: "flow_update",
                action: "set_flow",
                flow: event.flow,
              });
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        flowPreview: {
                          flow: event.flow,
                          name: event.name,
                          nodeCount: event.node_count,
                          edgeCount: event.edge_count,
                          graph: event.graph,
                        },
                      }
                    : msg,
                ),
              );
            },
            onFlowUpdate: (event) => {
              if (event.action === "edit_field") {
                // Add to flowActions for user review (don't apply immediately)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? {
                          ...msg,
                          flowActions: [
                            ...(msg.flowActions ?? []),
                            {
                              id: event.id as string,
                              type: "edit_field" as const,
                              description: event.description as string,
                              component_id: event.component_id as string,
                              component_type: event.component_type as string,
                              field: event.field as string,
                              old_value: event.old_value,
                              new_value: event.new_value,
                              patch: event.patch as {
                                op: string;
                                path: string;
                                value: unknown;
                              }[],
                              status: "pending" as const,
                            },
                          ],
                        }
                      : msg,
                  ),
                );
              } else {
                applyFlowUpdate(event);
              }
            },
            onComplete: (event) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        status: "complete",
                        content: event.data.result || "",
                        result: {
                          content: event.data.result || "",
                          validated: event.data.validated,
                          hasFlow: event.data.has_flow,
                          className: event.data.class_name,
                          componentCode: event.data.component_code,
                          validationAttempts: event.data.validation_attempts,
                          validationError: event.data.validation_error,
                        },
                      }
                    : msg,
                ),
              );
              setCurrentStep(null);
              setIsProcessing(false);
            },
            onError: (event) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        status: "error",
                        error: event.message,
                      }
                    : msg,
                ),
              );
              setCurrentStep(null);
              setIsProcessing(false);
            },
            onCancelled: () => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? {
                        ...msg,
                        status: "cancelled",
                        progress: undefined,
                      }
                    : msg,
                ),
              );
              setCurrentStep(null);
              setIsProcessing(false);
            },
          },
          abortControllerRef.current.signal,
        );
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    status: "error",
                    error: "Failed to connect to assistant",
                  }
                : msg,
            ),
          );
        }
        setCurrentStep(null);
        setIsProcessing(false);
      }
    },
    [isProcessing, currentFlowId],
  );

  const handleApprove = useCallback(
    async (messageId: string) => {
      const message = messages.find((m) => m.id === messageId);
      if (!message?.result?.componentCode) return;

      try {
        // Backend builds the full frontend_node from code validation; empty placeholder is expected
        const response = await validateComponent({
          code: message.result.componentCode,
          frontend_node: {} as APIClassType,
        });

        if (response.data) {
          addComponent(response.data, response.type || "CustomComponent");
        }
      } catch (error) {
        console.error("Failed to validate or add component to canvas:", error);
      }
    },
    [messages, validateComponent, addComponent],
  );

  const handleStopGeneration = useCallback(() => {
    abortControllerRef.current?.abort();

    setMessages((prev) =>
      prev.map((msg) =>
        msg.status === "streaming"
          ? {
              ...msg,
              status: "cancelled",
              progress: undefined,
            }
          : msg,
      ),
    );
    setCurrentStep(null);
    setIsProcessing(false);
  }, []);

  const handleUpdateFlowAction = useCallback(
    (messageId: string, actionId: string, status: "applied" | "dismissed") => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                flowActions: msg.flowActions?.map((a) =>
                  a.id === actionId ? { ...a, status } : a,
                ),
              }
            : msg,
        ),
      );
    },
    [],
  );

  const handleClearHistory = useCallback(() => {
    abortControllerRef.current?.abort();
    setMessages([]);
    setCurrentStep(null);
    setIsProcessing(false);
    sessionIdRef.current = uid.randomUUID(16);
  }, []);

  return {
    messages,
    isProcessing,
    currentStep,
    handleSend,
    handleApprove,
    handleUpdateFlowAction,
    handleStopGeneration,
    handleClearHistory,
  };
}
