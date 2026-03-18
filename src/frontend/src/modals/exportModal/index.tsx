import { forwardRef, type ReactNode, useEffect, useState } from "react";
import { track } from "@/customization/utils/analytics";
import useFlowStore from "@/stores/flowStore";
import type { FlowType } from "@/types/flow";
import IconComponent from "../../components/common/genericIconComponent";
import EditFlowSettings from "../../components/core/editFlowSettingsComponent";
import { Checkbox } from "../../components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Button } from "../../components/ui/button";
import { Copy, Download, ExternalLink, Loader2 } from "lucide-react";
import { API_WARNING_NOTICE_ALERT } from "../../constants/alerts_constants";
import {
  ALERT_SAVE_WITH_API,
  EXPORT_DIALOG_SUBTITLE,
  SAVE_WITH_API_CHECKBOX,
} from "../../constants/constants";
import useAlertStore from "../../stores/alertStore";
import { useDarkStore } from "../../stores/darkStore";
import { downloadFlow, removeApiKeys } from "../../utils/reactflowUtils";
import BaseModal from "../baseModal";

interface WXOExportData {
  toolkit_config: string;
  agent_yaml: string;
  import_commands: string;
}

const ExportModal = forwardRef(
  (
    props: {
      children?: ReactNode;
      open?: boolean;
      setOpen?: (open: boolean) => void;
      flowData?: FlowType;
    },
    ref,
  ): JSX.Element => {
    const version = useDarkStore((state) => state.version);
    const setSuccessData = useAlertStore((state) => state.setSuccessData);
    const setErrorData = useAlertStore((state) => state.setErrorData);
    const setNoticeData = useAlertStore((state) => state.setNoticeData);
    const [checked, setChecked] = useState(false);
    const currentFlowOnPage = useFlowStore((state) => state.currentFlow);
    const currentFlow = props.flowData ?? currentFlowOnPage;
    const isBuilding = useFlowStore((state) => state.isBuilding);
    const [locked, setLocked] = useState<boolean>(currentFlow?.locked ?? false);
    const [activeTab, setActiveTab] = useState<string>("standard");
    const [wxoLoading, setWxoLoading] = useState(false);
    const [wxoData, setWxoData] = useState<WXOExportData | null>(null);
    const [wxoActiveTab, setWxoActiveTab] = useState<string>("overview");

    useEffect(() => {
      setName(currentFlow?.name ?? "");
      setDescription(currentFlow?.description ?? "");
    }, [currentFlow?.name, currentFlow?.description]);
    const [name, setName] = useState(currentFlow?.name ?? "");
    const [description, setDescription] = useState(
      currentFlow?.description ?? "",
    );

    const [customOpen, customSetOpen] = useState(false);
    const [open, setOpen] =
      props.open !== undefined && props.setOpen !== undefined
        ? [props.open, props.setOpen]
        : [customOpen, customSetOpen];

    // Load watsonx Orchestrate export data when tab is activated
    useEffect(() => {
      if (activeTab === "watsonx" && !wxoData && !wxoLoading && currentFlow?.id) {
        loadWXOData();
      }
    }, [activeTab, currentFlow?.id, wxoData, wxoLoading]);

    const loadWXOData = async () => {
      if (!currentFlow?.id) {
        setErrorData({
          title: "No flow selected",
          list: ["Please save your flow before exporting to watsonx Orchestrate"],
        });
        return;
      }
      
      // Get the folder_id (project_id) from the current flow
      const projectId = currentFlow.folder_id || currentFlow.id;
      
      setWxoLoading(true);
      try {
        // Use the correct API endpoint with folder_id (project_id)
        const response = await fetch(`/api/v1/wxo/${projectId}/export`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate the response data structure
        if (!data.toolkit_config || !data.agent_yaml) {
          throw new Error("Invalid response format from server");
        }
        
        // Build import commands from the response
        const importCommands = [
          "# Import Toolkit",
          data.cli_import_command || "",
          "",
          "# Create Agent",
          data.agent_import_command || "",
        ].join("\n");
        
        setWxoData({
          toolkit_config: JSON.stringify(data.toolkit_config, null, 2),
          agent_yaml: data.agent_yaml,
          import_commands: importCommands,
        });
        setSuccessData({ title: "watsonx Orchestrate export data loaded" });
      } catch (error: any) {
        console.error("WXO Export Error:", error);
        setErrorData({
          title: "Failed to load watsonx Orchestrate data",
          list: [error.message || "Unknown error occurred"],
        });
      } finally {
        setWxoLoading(false);
      }
    };

    const handleCopy = (text: string, label: string) => {
      navigator.clipboard.writeText(text);
      setSuccessData({ title: `${label} copied to clipboard!` });
    };

    const handleDownloadFile = (content: string, filename: string) => {
      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSuccessData({ title: `${filename} downloaded successfully!` });
    };

    const handleStandardExport = async () => {
      try {
        let flowToExport: FlowType = {
          id: currentFlow!.id,
          data: currentFlow!.data!,
          description,
          name,
          last_tested_version: version,
          endpoint_name: currentFlow!.endpoint_name,
          is_component: false,
          tags: currentFlow!.tags,
          locked,
        };

        if (checked) {
          await downloadFlow(flowToExport, name!, description);
          setNoticeData({
            title: API_WARNING_NOTICE_ALERT,
          });
          setOpen(false);
          track("Flow Exported", { flowId: currentFlow!.id });
        } else {
          await downloadFlow(
            removeApiKeys(flowToExport),
            name!,
            description,
          );
          setSuccessData({
            title: "Flow exported successfully",
          });
          setOpen(false);
          track("Flow Exported", { flowId: currentFlow!.id });
        }
      } catch (error: any) {
        const detail = error?.response?.data?.detail;
        setErrorData({
          title: "Failed to export flow",
          ...(detail ? { list: [detail] } : {}),
        });
      }
    };

    return (
      <BaseModal
        size="large-h-full"
        open={open}
        setOpen={setOpen}
        onSubmit={activeTab === "standard" ? handleStandardExport : undefined}
      >
        <BaseModal.Trigger asChild>{props.children ?? <></>}</BaseModal.Trigger>
        <BaseModal.Header description={EXPORT_DIALOG_SUBTITLE}>
          <span className="pr-2">Export</span>
          <IconComponent
            name="Download"
            className="h-6 w-6 pl-1 text-foreground"
            aria-hidden="true"
          />
        </BaseModal.Header>
        <BaseModal.Content>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="standard">Standard Export</TabsTrigger>
              <TabsTrigger value="watsonx">
                <IconComponent name="Sparkles" className="mr-2 h-4 w-4" />
                watsonx Orchestrate
              </TabsTrigger>
            </TabsList>

            {/* Standard Export Tab */}
            <TabsContent value="standard" className="space-y-4">
              <EditFlowSettings
                name={name}
                description={description}
                setName={setName}
                setDescription={setDescription}
                locked={locked}
                setLocked={setLocked}
              />
              <div className="mt-3 flex items-center space-x-2">
                <Checkbox
                  id="terms"
                  checked={checked}
                  onCheckedChange={(event: boolean) => {
                    setChecked(event);
                  }}
                />
                <label htmlFor="terms" className="export-modal-save-api text-sm">
                  {SAVE_WITH_API_CHECKBOX}
                </label>
              </div>
              <span className="mt-1 text-xs text-destructive">
                {ALERT_SAVE_WITH_API}
              </span>
            </TabsContent>

            {/* watsonx Orchestrate Export Tab */}
            <TabsContent value="watsonx" className="space-y-4">
              {wxoLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <span className="ml-2">Loading watsonx Orchestrate export data...</span>
                </div>
              ) : wxoData ? (
                <Tabs value={wxoActiveTab} onValueChange={setWxoActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="toolkit">Toolkit Config</TabsTrigger>
                    <TabsTrigger value="agent">Agent YAML</TabsTrigger>
                    <TabsTrigger value="commands">Commands</TabsTrigger>
                  </TabsList>

                  {/* Overview Tab */}
                  <TabsContent value="overview" className="space-y-4">
                    <div className="rounded-lg border p-4 space-y-3">
                      <h3 className="font-semibold flex items-center">
                        <IconComponent name="Sparkles" className="mr-2 h-5 w-5 text-primary" />
                        Deploy to IBM watsonx Orchestrate
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Export this Langflow project as an enterprise AI agent skill for watsonx Orchestrate (Bob).
                        Your flow will be available as a production-ready skill with enterprise governance, security, and audit logging.
                      </p>
                      <div className="space-y-2 text-sm">
                        <p className="font-medium">What you'll get:</p>
                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                          <li>Toolkit configuration for watsonx Orchestrate</li>
                          <li>Agent YAML definition with all tools</li>
                          <li>Import commands for quick setup</li>
                          <li>Enterprise-grade security and governance</li>
                        </ul>
                      </div>
                      <div className="pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.open("https://www.ibm.com/products/watsonx-orchestrate", "_blank")}
                        >
                          <ExternalLink className="mr-2 h-4 w-4" />
                          Learn about watsonx Orchestrate
                        </Button>
                      </div>
                    </div>
                  </TabsContent>

                  {/* Toolkit Config Tab */}
                  <TabsContent value="toolkit" className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Toolkit Configuration (JSON)</label>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCopy(wxoData.toolkit_config, "Toolkit config")}
                          >
                            <Copy className="mr-2 h-4 w-4" />
                            Copy
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownloadFile(wxoData.toolkit_config, `${name}-toolkit-config.json`)}
                          >
                            <Download className="mr-2 h-4 w-4" />
                            Download
                          </Button>
                        </div>
                      </div>
                      <pre className="rounded-lg border bg-muted p-4 text-xs overflow-auto max-h-96">
                        <code>{wxoData.toolkit_config}</code>
                      </pre>
                    </div>
                  </TabsContent>

                  {/* Agent YAML Tab */}
                  <TabsContent value="agent" className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Agent Definition (YAML)</label>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCopy(wxoData.agent_yaml, "Agent YAML")}
                          >
                            <Copy className="mr-2 h-4 w-4" />
                            Copy
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownloadFile(wxoData.agent_yaml, `${name}-agent.yaml`)}
                          >
                            <Download className="mr-2 h-4 w-4" />
                            Download
                          </Button>
                        </div>
                      </div>
                      <pre className="rounded-lg border bg-muted p-4 text-xs overflow-auto max-h-96">
                        <code>{wxoData.agent_yaml}</code>
                      </pre>
                    </div>
                  </TabsContent>

                  {/* Commands Tab */}
                  <TabsContent value="commands" className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Import Commands</label>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(wxoData.import_commands, "Import commands")}
                        >
                          <Copy className="mr-2 h-4 w-4" />
                          Copy
                        </Button>
                      </div>
                      <pre className="rounded-lg border bg-muted p-4 text-xs overflow-auto max-h-96">
                        <code>{wxoData.import_commands}</code>
                      </pre>
                      <p className="text-xs text-muted-foreground mt-2">
                        Run these commands in your watsonx Orchestrate environment to import this agent.
                      </p>
                    </div>
                  </TabsContent>
                </Tabs>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Click "Load Export Data" to generate watsonx Orchestrate configuration</p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={loadWXOData}
                  >
                    Load Export Data
                  </Button>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </BaseModal.Content>

        {activeTab === "standard" ? (
          <BaseModal.Footer
            submit={{
              label: "Export",
              loading: isBuilding,
              dataTestId: "modal-export-button",
            }}
          />
        ) : (
          <BaseModal.Footer>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Close
            </Button>
          </BaseModal.Footer>
        )}
      </BaseModal>
    );
  },
);
export default ExportModal;

// Made with Bob
