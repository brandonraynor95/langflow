import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UpdateAllComponents from "../index";

const mockAddDismissedNodes = jest.fn();
const mockSetErrorData = jest.fn();
const mockTakeSnapshot = jest.fn();

let flowStoreState: any;

jest.mock("@xyflow/react", () => ({
  useUpdateNodeInternals: () => jest.fn(),
}));

jest.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: any) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

jest.mock("@/CustomNodes/helpers/process-node-advanced-fields", () => ({
  processNodeAdvancedFields: jest.fn(),
}));

jest.mock("@/CustomNodes/hooks/use-update-all-nodes", () => ({
  __esModule: true,
  default: () => jest.fn(),
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, loading, ...props }: any) => (
    <button onClick={onClick} data-loading={loading} {...props}>
      {children}
    </button>
  ),
}));

jest.mock("@/controllers/API/queries/nodes/use-post-validate-component-code", () => ({
  usePostValidateComponentCode: () => ({
    mutateAsync: jest.fn(),
  }),
}));

jest.mock("@/modals/updateComponentModal", () => () => null);

jest.mock("@/stores/alertStore", () => {
  const useAlertStore = (selector: any) =>
    selector({
      setErrorData: mockSetErrorData,
      setNoticeData: jest.fn(),
      setSuccessData: jest.fn(),
    });
  useAlertStore.getState = () => ({
    setErrorData: mockSetErrorData,
    setNoticeData: jest.fn(),
    setSuccessData: jest.fn(),
  });

  return {
    __esModule: true,
    default: useAlertStore,
  };
});

jest.mock("@/stores/flowStore", () => {
  const useFlowStore = (selector?: any) =>
    selector ? selector(flowStoreState) : flowStoreState;
  useFlowStore.getState = () => flowStoreState;

  return {
    __esModule: true,
    default: useFlowStore,
    registerNodeUpdate: jest.fn(),
    completeNodeUpdate: jest.fn(),
  };
});

jest.mock("@/stores/flowsManagerStore", () => ({
  __esModule: true,
  default: (selector: any) =>
    selector({
      takeSnapshot: mockTakeSnapshot,
    }),
}));

jest.mock("@/stores/typesStore", () => ({
  useTypesStore: (selector: any) =>
    selector({
      templates: {},
    }),
}));

jest.mock("@/stores/utilityStore", () => ({
  useUtilityStore: (selector: any) =>
    selector({
      allowCustomComponents: false,
    }),
}));

jest.mock("@/utils/utils", () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(" "),
}));

const mockSetNodes = jest.fn();

describe("UpdateAllComponents", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    flowStoreState = {
      componentsToUpdate: [
        {
          id: "node-1",
          display_name: "Unknown Custom",
          icon: "box",
          outdated: false,
          blocked: true,
          breakingChange: false,
          userEdited: false,
        },
      ],
      nodes: [
        {
          id: "node-1",
          data: {
            type: "UnknownCustom",
            node: {
              edited: false,
              display_name: "Unknown Custom",
              template: { code: { value: "custom_code" } },
            },
          },
        },
      ],
      edges: [],
      setNodes: mockSetNodes,
      dismissedNodes: [],
      addDismissedNodes: mockAddDismissedNodes,
      isBuilding: false,
      buildInfo: null,
    };
  });

  it("dismiss marks nodes as edited via setNodes", async () => {
    const user = userEvent.setup();

    render(<UpdateAllComponents />);

    await user.click(screen.getByRole("button", { name: /dismiss/i }));

    expect(mockAddDismissedNodes).toHaveBeenCalledWith(["node-1"]);
    expect(mockSetNodes).toHaveBeenCalled();
  });
});
