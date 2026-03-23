import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryKnowledgeBaseSection } from "../MemoryKnowledgeBaseSection";

jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }: { name: string }) => <span>{name}</span>,
}));

jest.mock("@/components/ui/loading", () => ({
  __esModule: true,
  default: () => <div>loading...</div>,
}));

describe("MemoryKnowledgeBaseSection", () => {
  const baseProps = {
    docsData: {
      total: 1,
      sessions: ["session-1"],
      documents: [
        {
          message_id: "msg-1",
          session_id: "session-1",
          sender: "user",
          content: "hello",
          timestamp: "2025-01-01T10:00:00.000Z",
        },
      ],
    },
    docsLoading: false,
    searchQuery: "",
    setSearchQuery: jest.fn(),
    activeSearch: "",
    setActiveSearch: jest.fn(),
    selectedSession: null,
    setSelectedSession: jest.fn(),
    handleSearch: jest.fn(),
    groupedBySession: new Map([
      [
        "session-1",
        [
          {
            message_id: "msg-1",
            session_id: "session-1",
            sender: "user",
            content: "hello",
            timestamp: "2025-01-01T10:00:00.000Z",
          },
        ],
      ],
    ]),
    handleOpenDocumentPanel: jest.fn(),
    totalChunks: 1,
  } as any;

  it("shows loading state", () => {
    render(<MemoryKnowledgeBaseSection {...baseProps} docsLoading />);
    expect(screen.getByText("loading...")).toBeInTheDocument();
  });

  it("opens document panel when row is clicked", () => {
    render(<MemoryKnowledgeBaseSection {...baseProps} />);

    fireEvent.click(screen.getByText("hello"));
    expect(baseProps.handleOpenDocumentPanel).toHaveBeenCalled();
  });

  it("clears active search", () => {
    render(
      <MemoryKnowledgeBaseSection
        {...baseProps}
        activeSearch="abc"
        searchQuery="abc"
      />,
    );

    const clearButton = screen.getAllByRole("button")[1];
    fireEvent.click(clearButton);
    expect(baseProps.setSearchQuery).toHaveBeenCalledWith("");
    expect(baseProps.setActiveSearch).toHaveBeenCalledWith("");
  });
});
