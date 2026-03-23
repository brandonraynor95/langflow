import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryDetailsHeader } from "../MemoryDetailsHeader";

jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }: { name: string }) => <span>{name}</span>,
}));

jest.mock("@/components/ui/switch", () => ({
  Switch: ({ onCheckedChange, checked }: any) => (
    <input
      type="checkbox"
      aria-label="auto-capture"
      checked={checked}
      onChange={(e) => onCheckedChange(e.target.checked)}
    />
  ),
}));

jest.mock("@/modals/deleteConfirmationModal", () => ({
  __esModule: true,
  default: ({ children, onConfirm }: any) => (
    <div>
      {children}
      <button onClick={() => onConfirm({ stopPropagation: jest.fn() })}>confirm-delete</button>
    </div>
  ),
}));

describe("MemoryDetailsHeader", () => {
  const baseProps = {
    memory: {
      id: "m1",
      name: "Memory One",
      description: "desc",
      status: "idle",
      is_active: true,
    },
    isProcessing: false,
    manualUpdateMutation: { mutate: jest.fn(), isPending: false },
    handleManualUpdate: jest.fn(),
    deleteMutation: { mutate: jest.fn() },
    updateMemoryMutation: { isPending: false },
    handleToggleActive: jest.fn(),
  } as any;

  it("renders memory information", () => {
    render(<MemoryDetailsHeader {...baseProps} />);
    expect(screen.getByText("Memory One")).toBeInTheDocument();
    expect(screen.getByText("Auto-capture on")).toBeInTheDocument();
  });

  it("calls mutate handlers for actions", () => {
    render(<MemoryDetailsHeader {...baseProps} />);

    fireEvent.click(screen.getByText("Update Memory"));
    expect(baseProps.handleManualUpdate).toHaveBeenCalled();

    fireEvent.click(screen.getByText("confirm-delete"));
    expect(baseProps.deleteMutation.mutate).toHaveBeenCalledWith({ memoryId: "m1" });
  });

  it("toggles auto-capture", () => {
    render(<MemoryDetailsHeader {...baseProps} />);
    fireEvent.click(screen.getByLabelText("auto-capture"));
    expect(baseProps.handleToggleActive).toHaveBeenCalled();
  });
});
