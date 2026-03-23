import { act, renderHook } from "@testing-library/react";
import { useMemoriesData } from "../useMemoriesData";

const mockSetErrorData = jest.fn();
const mockSetSuccessData = jest.fn();

jest.mock("@/stores/alertStore", () => ({
  __esModule: true,
  default: () => ({
    setErrorData: mockSetErrorData,
    setSuccessData: mockSetSuccessData,
  }),
}));

const memories = [
  {
    id: "m1",
    name: "First",
    description: "alpha",
    status: "idle",
    is_active: true,
  },
  {
    id: "m2",
    name: "Second",
    description: "beta",
    status: "idle",
    is_active: false,
  },
] as any;

jest.mock("@/controllers/API/queries/memories/use-get-memories", () => ({
  useGetMemories: () => ({ data: memories }),
}));

jest.mock("@/controllers/API/queries/memories/use-get-memory", () => ({
  useGetMemory: () => ({
    data: {
      id: "m1",
      status: "idle",
      is_active: true,
      documents: [{ message_id: "msg1", session_id: "s1", content: "hello" }],
      document_sessions: ["s1"],
      documents_total: 1,
    },
    isLoading: false,
    isError: false,
  }),
}));

const mutation = { mutate: jest.fn(), isPending: false };
jest.mock(
  "@/controllers/API/queries/memories/use-add-messages-to-memory",
  () => ({
    useAddMessagesToMemory: () => mutation,
  }),
);
jest.mock("@/controllers/API/queries/memories/use-delete-memory", () => ({
  useDeleteMemory: () => mutation,
}));
jest.mock("@/controllers/API/queries/memories/use-update-memory", () => ({
  useUpdateMemory: () => mutation,
}));

describe("useMemoriesData", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("auto-selects first memory when no selection", () => {
    const onSelectMemory = jest.fn();

    renderHook(() =>
      useMemoriesData({
        currentFlowId: "flow-1",
        selectedMemoryId: null,
        onSelectMemory,
      }),
    );

    expect(onSelectMemory).toHaveBeenCalledWith("m1");
  });

  it("filters memories by search query", () => {
    const { result } = renderHook(() =>
      useMemoriesData({
        currentFlowId: "flow-1",
        selectedMemoryId: "m1",
        onSelectMemory: jest.fn(),
      }),
    );

    act(() => {
      result.current.setMemoriesSearch("second");
    });

    expect(result.current.filteredMemories).toHaveLength(1);
    expect(result.current.filteredMemories[0].id).toBe("m2");
  });

  it("opens document panel for selected document", () => {
    const { result } = renderHook(() =>
      useMemoriesData({
        currentFlowId: "flow-1",
        selectedMemoryId: "m1",
        onSelectMemory: jest.fn(),
      }),
    );

    act(() => {
      result.current.handleOpenDocumentPanel({ message_id: "msg1" } as any);
    });

    expect(result.current.documentPanelOpen).toBe(true);
    expect(result.current.selectedDocument?.message_id).toBe("msg1");
  });
});
