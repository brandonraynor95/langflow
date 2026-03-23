import type {
  AgenticProgressState,
  AgenticResult,
  AgenticStepType,
  FlowAction,
} from "@/controllers/API/queries/agentic";

export type AssistantMessageStatus =
  | "pending"
  | "streaming"
  | "complete"
  | "error"
  | "cancelled";

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  status?: AssistantMessageStatus;
  progress?: AgenticProgressState;
  completedSteps?: AgenticStepType[];
  result?: AgenticResult;
  error?: string;
  flowPreview?: {
    flow: Record<string, unknown>;
    name: string;
    nodeCount: number;
    edgeCount: number;
    graph: string;
  };
  flowActions?: FlowAction[];
}

export interface AssistantModel {
  id: string;
  name: string;
  provider: string;
  displayName: string;
}

export interface AssistantSuggestion {
  id: string;
  icon: string;
  text: string;
}

export interface AssistantPanelProps {
  isOpen: boolean;
  onClose: () => void;
}
