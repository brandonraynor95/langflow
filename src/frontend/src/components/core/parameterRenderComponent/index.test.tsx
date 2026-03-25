import type { ComponentProps } from "react";
import { render, screen } from "@testing-library/react";
import { ParameterRenderComponent } from ".";

let mockCloudOnly = false;
type CloudModeState = {
  cloudOnly: boolean;
  setCloudOnly: jest.Mock;
};
type StrRenderProps = {
  value?: string | number | readonly string[] | null;
  placeholder?: string | null;
};

jest.mock("@/stores/cloudModeStore", () => ({
  useCloudModeStore: <T,>(selector: (state: CloudModeState) => T) =>
    selector({ cloudOnly: mockCloudOnly, setCloudOnly: jest.fn() }),
}));

jest.mock("./components/strRenderComponent", () => ({
  StrRenderComponent: ({ value, placeholder }: StrRenderProps) => (
    <div
      data-testid="str-render-props"
      data-value={value ?? ""}
      data-placeholder={placeholder ?? ""}
    />
  ),
}));

jest.mock("./components/mcpComponent", () => () => (
  <div data-testid="mcp-component" />
));

describe("ParameterRenderComponent", () => {
  beforeEach(() => {
    mockCloudOnly = false;
  });

  const baseProps: ComponentProps<typeof ParameterRenderComponent> = {
    handleOnNewValue: jest.fn(),
    name: "url",
    nodeId: "test-node-id",
    editNode: true,
    showParameter: true,
    inspectionPanel: false,
    handleNodeClass: jest.fn(),
    nodeClass: {
      description: "Test component",
      template: {},
      display_name: "Test Component",
      documentation: "Test component documentation",
      metadata: {
        cloud_default_overrides: {
          url: {
            value: "",
            placeholder: "Enter your cloud URL",
          },
        },
      },
    },
    disabled: false,
    templateData: { type: "str", name: "url", placeholder: "Local URL" },
  };

  it("keeps an existing saved value visible in cloud mode", () => {
    mockCloudOnly = true;

    render(
      <ParameterRenderComponent
        {...baseProps}
        templateValue="https://prod.example.com"
      />,
    );

    const renderedProps = screen.getByTestId("str-render-props");
    expect(renderedProps).toHaveAttribute(
      "data-value",
      "https://prod.example.com",
    );
    expect(renderedProps).toHaveAttribute("data-placeholder", "Local URL");
  });

  it("uses the cloud placeholder when a new value is empty", () => {
    mockCloudOnly = true;

    render(<ParameterRenderComponent {...baseProps} templateValue="" />);

    const renderedProps = screen.getByTestId("str-render-props");
    expect(renderedProps).toHaveAttribute("data-value", "");
    expect(renderedProps).toHaveAttribute(
      "data-placeholder",
      "Enter your cloud URL",
    );
  });
});
