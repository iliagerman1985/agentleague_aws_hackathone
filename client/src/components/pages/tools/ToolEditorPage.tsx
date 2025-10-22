import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Save, MessageCircle, Code, FlaskConical, Edit3, Check, X, ArrowLeft } from "lucide-react";
import { TestDialog } from "@/components/tools/TestDialog";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toolsService, type ToolValidationStatus } from "@/services/toolsService";
import { toolAgentService } from "@/services/toolAgentService";
import type { ChatMessage } from "@/components/tools/VibeChat";
import { type ToolId } from "@/types/ids";
import { type ModelSelection } from "@/lib/api";
import { loadGameEnvironmentMetadata, type GameEnvironmentMetadata, getAvailableGameEnvironments } from "@/services/agentsService";
import { getEnvironmentTheme } from "@/lib/environmentThemes";
import { GameEnvironment } from "@/types/game";



import { ErrorBoundary } from "@/components/common/utility/ErrorBoundary";
// Removed PanelGroup; unified responsive layout uses CSS grid
import { runCodeStreaming, extractPackagesFromCode } from "@/services/pythonRuntime";
import { useToolsLLM } from "@/contexts/LLMContext";
import { useLLM } from "@/contexts/LLMContext";

import VibeChat from "@/components/tools/VibeChat";
import { LLMSelectorWrapper } from "@/components/common";
import { MessageContent } from "@/components/tools/MessageContent";
import LLMIntegrationDialog from "@/components/llm/LLMIntegrationDialog";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";

export const ToolEditorPage: React.FC = () => {
  const { id } = useParams();
  const isNew = id === undefined; // route /tools/new has no id param
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const rt = params.get("returnTo");
    return rt ? decodeURIComponent(rt) : null;
  }, [location.search]);
  const { selectedModel, availableIntegrations } = useToolsLLM();
  const { refreshIntegrations } = useLLM();



  const [displayName, setDisplayName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState(""); // using description to match backend
  const [environment, setEnvironment] = useState<GameEnvironment>(GameEnvironment.CHESS);
  const [loading, setLoading] = useState(!isNew);
  const [isSystemTool, setIsSystemTool] = useState(false);

  // Environment selection dialog for new tools
  const [showEnvironmentDialog, setShowEnvironmentDialog] = useState(isNew);
  const [envMetadata, setEnvMetadata] = useState<Record<GameEnvironment, GameEnvironmentMetadata> | null>(null);
  const [loadingEnv, setLoadingEnv] = useState(false);

  // State for inline description editing
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const [editingDescription, setEditingDescription] = useState("");

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const [logs, setLogs] = useState<string[]>([]);


  // Load environment metadata on mount
  useEffect(() => {
    if (!envMetadata && !loadingEnv) {
      setLoadingEnv(true);
      loadGameEnvironmentMetadata()
        .then((data) => {
          setEnvMetadata(data);
        })
        .catch(() => {
          // Silently fail - we'll use defaults
        })
        .finally(() => setLoadingEnv(false));
    }
  }, [envMetadata, loadingEnv]);

  // Expose a setter hook for E2E to set code deterministically
  // Safe in production: it only exposes a function on window; real users never call it
  useEffect(() => {
    (window as any).__setToolCode = (val: string) => setCode(String(val ?? ""));
    return () => {
      try { delete (window as any).__setToolCode; } catch {}
    };
  }, []);
  const [status, setStatus] = useState<"idle" | "running" | "passed" | "failed">("idle");
  const [running, setRunning] = useState(false);
  const [validationStatus, setValidationStatus] = useState<ToolValidationStatus>("pending");

  // UI state
  const [mobileTab, setMobileTab] = useState<"chat" | "code" | "desc">("chat");
  const [showTestDialog, setShowTestDialog] = useState(false);

  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [, setSuggestedPkgs] = useState<string[]>([]);

  const [generatedTestJson, setGeneratedTestJson] = useState<string>("");
  const [showLLMDialog, setShowLLMDialog] = useState(false);


  // Use the shared function from pythonRuntime
  const suggestPackagesFromCode = extractPackagesFromCode;

  // Helper function to convert ChatMessage to AgentMessage
  const convertToAgentMessage = (msg: ChatMessage): Record<string, any> => ({
    writer: msg.role === "user" ? "human" : "agent",
    content: msg.text,
    timestamp: new Date().toISOString(),
  });

  // Helper function to extract function description from LLM response
  const extractFunctionDescription = (text: string): string | null => {
    // Look for the function description pattern in the response
    const descriptionMatch = text.match(/\*\*Function Description:\*\*\s*\n(.*?)(?:\n\n|\*\*|$)/s);
    if (descriptionMatch) {
      let description = descriptionMatch[1].trim();

      // Also try to extract required parameters
      const paramsMatch = text.match(/\*\*Required Parameters:\*\*\s*\n(.*?)(?:\n\n|\*\*|$)/s);
      if (paramsMatch) {
        const params = paramsMatch[1].trim();
        description += "\n\nRequired Parameters:\n" + params;
      }

      // Also try to extract return format
      const returnsMatch = text.match(/\*\*Returns:\*\*\s*\n(.*?)(?:\n\n|\*\*|$)/s);
      if (returnsMatch) {
        const returns = returnsMatch[1].trim();
        description += "\n\nReturns:\n" + returns;
      }

      return description;
    }

    // Fallback: try to extract any description near code blocks
    const codeBlockMatch = text.match(/```tool-function[\s\S]*?```\s*\n*(.*?)(?:\n\n|$)/);
    if (codeBlockMatch) {
      const afterCode = codeBlockMatch[1].trim();
      if (afterCode && afterCode.length > 10 && afterCode.length < 500) {
        return afterCode;
      }
    }

    return null;
  };

  // Extract new structured sections by headings (Description, OpenAPI, Examples)
  const extractStructuredDescription = (text: string): string | null => {
    const hDesc = "### Human-Readable Description";
    const hOpen = "### OpenAPI Schema";
    const hEx = "### Usage Examples";

    const markers = [
      { key: "desc", idx: text.indexOf(hDesc) },
      { key: "openapi", idx: text.indexOf(hOpen) },
      { key: "examples", idx: text.indexOf(hEx) },
    ]
      .filter((m) => m.idx !== -1)
      .sort((a, b) => a.idx - b.idx);

    if (markers.length === 0) return null;

    const slice = (start: number, end?: number) => text.slice(start, end ?? text.length).trim();
    const parts: string[] = [];
    for (let i = 0; i < markers.length; i++) {
      const cur = markers[i];
      const next = markers[i + 1];
      parts.push(slice(cur.idx, next?.idx));
    }
    return parts.join("\n\n");
  };

  useEffect(() => {
    if (!isNew && id) {
      toolsService.get(id as ToolId).then((t) => {
        if (!t) {
          navigate("/tools");
          return;
        }
        setDisplayName(t.displayName);
        setCode(t.code);
        setDescription(t.description ?? "");
        setEnvironment(t.environment);
        setIsSystemTool(t.isSystem);
        try { setValidationStatus(t.validationStatus as ToolValidationStatus); } catch {}

        // Add initial chat message with the tool code
        const initialMessage: ChatMessage = {
          id: "initial-code",
          role: "assistant",
          text: `Here's the current tool code:\n\n\`\`\`python\n${t.code}\n\`\`\``,
        };
        setChatMessages([initialMessage]);

      }).finally(() => setLoading(false));
    }
  }, [id, isNew, navigate]);

  const handleSave = async () => {
    if (!displayName.trim() || !description.trim()) return; // validated beforehand
    try {
      if (isNew) {
        console.log('Creating tool with:', { display_name: displayName.trim(), code, description, environment });
        const tool = await toolsService.create({ display_name: displayName.trim(), code, description, environment });
        console.log('Tool created successfully:', tool);
        // If user ran a test before saving, propagate that result to backend now
        try {
          if (status === "passed") {
            await toolsService.setValidationStatus(tool.id as ToolId, "valid");
            setValidationStatus("valid");
          } else if (status === "failed") {
            await toolsService.setValidationStatus(tool.id as ToolId, "error");
            setValidationStatus("error");
          }
        } catch {}
        if (returnTo) {
          // Navigate back to the originating page (e.g., agent editor)
          // If returning to agent editor, open the tools tab
          if (returnTo.includes('/agents/')) {
            navigate(returnTo, { state: { initialTab: 'tools' } });
          } else {
            navigate(returnTo);
          }
        } else {
          navigate(`/tools/${tool.id}`);
        }
      } else if (id && isSystemTool) {
        // Clone system tool instead of updating
        console.log('Cloning system tool:', id);
        const clonedTool = await toolsService.clone(id as ToolId);
        console.log('Tool cloned successfully:', clonedTool);
        // Navigate to the cloned tool for editing
        navigate(`/tools/${clonedTool.id}`);
      } else if (id) {
        await toolsService.update(id as ToolId, { display_name: displayName.trim(), code, description, environment });
        // Propagate latest test result after update as well
        try {
          if (status === "passed") {
            await toolsService.setValidationStatus(id as ToolId, "valid");
            setValidationStatus("valid");
          } else if (status === "failed") {
            await toolsService.setValidationStatus(id as ToolId, "error");
            setValidationStatus("error");
          }
        } catch {}
      }
      setShowSaveDialog(false);
    } catch (error) {
      console.error('Error saving tool:', error);
      // For now, just log the error and keep the dialog open
      // In a real app, we'd show a toast notification
    }
  };

  const handleEditDescription = () => {
    setEditingDescription(description);
    setIsEditingDescription(true);
  };

  const handleSaveDescription = async () => {
    if (!isNew && id) {
      try {
        await toolsService.update(id as ToolId, { description: editingDescription });
        setDescription(editingDescription);
        setIsEditingDescription(false);
      } catch (error) {
        console.error('Failed to update description:', error);
        // Could add error toast here
      }
    } else {
      // For new tools, just update the local state
      setDescription(editingDescription);
      setIsEditingDescription(false);
    }
  };

  const handleCancelEditDescription = () => {
    setEditingDescription(description);
    setIsEditingDescription(false);
  };

  const handleTestJsonGenerated = (json: string) => {
    console.log('[DEBUG] Test JSON generated, storing and opening dialog');
    setGeneratedTestJson(json);
    // Open the dialog now that we have the test JSON
    openTestDialog();
  };

  // Helper to open test dialog and reset previous execution state
  const openTestDialog = () => {
    setStatus("idle");
    setLogs([]);
    setRunning(false);
    setShowTestDialog(true);
  };

  const handleRun = async (testEventJson: string) => {
    try {
      setStatus("running");
      setRunning(true);
      setShowTestDialog(true);
      // Clear previous logs on each run
      setLogs([`Running handler at ${new Date().toLocaleTimeString()}...`]);

      // Debug: Log the code length to verify it's not empty
      console.log(`[DEBUG] Running test with code length: ${code.length} characters`);
      if (code.length === 0) {
        setLogs((l) => [...l, "ERROR: No code to execute. Please generate or enter code first."]);
        setStatus("failed");
        setRunning(false);
        return;
      }

      // Parse event JSON from the test dialog
      const event = JSON.parse(testEventJson || "{}");

      // Create complete code that defines the handler and calls it
      // Convert JSON to Python-compatible format (null -> None, true -> True, false -> False)
      const pythonEventStr = JSON.stringify(event)
        .replace(/\bnull\b/g, 'None')
        .replace(/\btrue\b/g, 'True')
        .replace(/\bfalse\b/g, 'False');

      const completeCode = `
${code}

# Call the handler function with the event
import json
import sys

event = ${pythonEventStr}
context = {}

try:
    result = lambda_handler(event, context)
    if result is not None:
        if isinstance(result, (dict, list)):
            print(json.dumps(result, indent=2))
        else:
            print(str(result))
    else:
        print("Function returned None")
except Exception as e:
    print(f"Error executing lambda_handler: {str(e)}")
    import traceback
    traceback.print_exc()
    raise
`;

      console.log(`[DEBUG] Complete code to execute:\n${completeCode.substring(0, 200)}...`);

      const out = await runCodeStreaming(completeCode, {
        onStdout: (msg) => setLogs((l) => [...l, msg]),
        onStderr: (msg) => setLogs((l) => [...l, msg])
      });

      if (out.stderr && out.stderr.trim()) {
        setStatus("failed");
        // Update validation status to error when execution produces stderr
        if (!isNew && id) {
          try {
            await toolsService.setValidationStatus(id as ToolId, "error");
            setValidationStatus("error");
          } catch {}
        }
        // stderr is already captured by onStderr callback, no need to add again
      } else {
        setStatus("passed");
        // Mark tool as valid on successful run
        if (!isNew && id) {
          try {
            await toolsService.setValidationStatus(id as ToolId, "valid");
            setValidationStatus("valid");
          } catch {}
        }
        // stdout is already captured by onStdout callback, no need to add again
        // Only add a message if there was truly no output
        if (!out.stdout || !out.stdout.trim()) {
          setLogs((l) => [...l, "Function executed successfully but produced no output"]);
        }
      }
    } catch (e) {
      setStatus("failed");
      // Update validation status to error on exception
      if (!isNew && id) {
        try {
          await toolsService.setValidationStatus(id as ToolId, "error");
          setValidationStatus("error");
        } catch {}
      }
      setLogs((l) => [...l, "Run failed: " + String(e)]);
    } finally {
      // always reset running so the Run buttons become active again
      setRunning(false);
    }
  };

  const handleAttemptFix = async (outputText: string) => {
    const text = String(outputText || "").trim();
    if (!text) return;

    // Close the test dialog immediately and focus chat
    setShowTestDialog(false);
    setMobileTab("chat");

    const prompt = `The tool test just failed. Here is the full output from running the tool.\n\n\u0060\u0060\u0060text\n${text}\n\u0060\u0060\u0060\nPlease diagnose the issue and provide a corrected version of the tool function. Return only the updated tool function in a single code block labeled \"tool-function\".`;
    await onSendChat(prompt, undefined, selectedModel ?? undefined);
  };




  const onSendChat = async (text: string, replyTo?: string, modelSelection?: ModelSelection): Promise<boolean> => {
    const effectiveModel = modelSelection || selectedModel;

    // Preflight: verify the selected integration exists and is active in the current context
    const integrationValid = !!(effectiveModel && effectiveModel.integrationId &&
      availableIntegrations?.some((i) => i.id === effectiveModel.integrationId && i.isActive));

    if (!integrationValid) {
      setShowLLMDialog(true);
      return false; // indicate message was not accepted; keep it in the input
    }

    const userMessageId = Math.random().toString(36).slice(2);
    setChatMessages((m) => [...m, { id: userMessageId, role: "user", text, replyTo }]);
    setIsTyping(true);

    try {
      // Convert chat messages to agent message format
      const conversationHistory = chatMessages.map(convertToAgentMessage);

      // Stream the response
      const assistantMessageId = userMessageId + "-a";
      let codeGenerated = false;

      let accumulatedContent = "";
      let hasStartedResponse = false;

      // Stream using tool agent service
      for await (const chunk of toolAgentService.streamChat({
        message: text,
        conversation_history: conversationHistory,
        integration_id: effectiveModel.integrationId,
        model_id: effectiveModel.modelId,
        environment: environment as GameEnvironment,
        current_tool_code: code, // Pass current code for context
      })) {
        if (chunk.type === "content" && chunk.content) {
          accumulatedContent += chunk.content;

          if (!hasStartedResponse) {
            // Add the assistant message for the first time
            setChatMessages((m) => [...m, { id: assistantMessageId, role: "assistant", text: accumulatedContent }]);
            hasStartedResponse = true;
          } else {
            // Update the existing assistant message
            setChatMessages((m) =>
              m.map((msg) => (msg.id === assistantMessageId ? { ...msg, text: accumulatedContent } : msg))
            );
          }
        } else if (chunk.type === "tool" && chunk.tool_artifact) {
          codeGenerated = true;

          // Handle tool artifact - update the code editor and show modal preview
          const generatedCode = chunk.tool_artifact.code || "";

          // Backend can send description in two ways:
          // 1. In the chunk.description field (sent separately by service)
          // 2. In the chunk.tool_artifact.explanation field (from CodeArtifact)
          const toolExplanation = (chunk as any).description || (chunk.tool_artifact as any).explanation;

          console.log(`[DEBUG] Generated code received, length: ${generatedCode.length}`);
          console.log(`[DEBUG] Generated code preview:\n${generatedCode.substring(0, 300)}...`);
          console.log(`[DEBUG] Tool explanation: ${toolExplanation || '(none)'}`);

          setCode(generatedCode);

          // Extract and suggest packages
          const pkgs = suggestPackagesFromCode(generatedCode);
          setSuggestedPkgs(pkgs);

          // Set description if provided in tool artifact
          if (toolExplanation && !description.trim()) {
            setDescription(toolExplanation);
          }

          // Auto-save the tool if we're editing an existing tool
          if (!isNew && id) {
            try {
              const updateData: any = { code: generatedCode };
              if (toolExplanation) {
                updateData.description = toolExplanation;
              }
              await toolsService.update(id as ToolId, updateData);
              console.log("Auto-saved generated code to tool");
            } catch (error) {
              console.error("Failed to auto-save generated code:", error);
            }
          }
        } else if (chunk.type === "test") {
          // Handle test JSON - can come from test_artifact or test_json field
          const testJson = (chunk as any).test_json;
          if (testJson) {
            console.log(`[DEBUG] Test JSON received: ${testJson.substring(0, 200)}...`);
            setGeneratedTestJson(testJson);
          } else if (chunk.test_artifact?.game_state) {
            setGeneratedTestJson(JSON.stringify(chunk.test_artifact.game_state, null, 2));
          }
        } else if (chunk.type === "done") {
          // Done chunk - check if there's test_json or description we haven't processed yet
          const testJson = (chunk as any).test_json;
          if (testJson) {
            console.log(`[DEBUG] Test JSON in done chunk: ${testJson.substring(0, 200)}...`);
            setGeneratedTestJson(testJson);
          }
        } else if (chunk.type === "error") {
          const errMsg = chunk.error;
          if (errMsg) {
            const lower = errMsg.toLowerCase();
            if (lower.includes("provider or integration unavailable")) {
              setShowLLMDialog(true);
            } else {
              const errorId = assistantMessageId + "-err";

              // Check if this is a guardrail violation
              const isGuardrailError = lower.includes("violates our usage policies") ||
                                       lower.includes("prohibited content") ||
                                       lower.includes("content policies");

              if (isGuardrailError) {
                setChatMessages((m) => [
                  ...m,
                  {
                    id: errorId,
                    role: "assistant",
                    text: `⚠️ **Content Policy Violation**\n\n${errMsg}\n\nPlease keep your messages focused on tool creation for your game environment.`
                  },
                ]);
              } else {
                setChatMessages((m) => [
                  ...m,
                  { id: errorId, role: "assistant", text: `Error from model/provider: ${errMsg}` },
                ]);
              }
            }
          }
        }
      }

      // Show completion message when tool code was generated
      if (codeGenerated) {
        const tipId = userMessageId + "-tip";
        setChatMessages((m) => [
          ...m,
          {
            id: tipId,
            role: "assistant",
            text: "TOOL_GENERATION_COMPLETE", // Special marker for completion message with buttons
          },
        ]);
      }

      // Fallback: if no explicit final payload was sent, parse accumulated content
      if (!description.trim() && accumulatedContent) {
        const structured = extractStructuredDescription(accumulatedContent);
        if (structured) {
          setDescription(structured);
          if (!isNew && id) {
            try {
              await toolsService.update(id as ToolId, { description: structured });
            } catch {}
          }
        }
      }

      return true; // indicate message was accepted and input can clear
    } catch (error) {
      console.error("Error in vibe chat:", error);
      const message = error instanceof Error ? error.message : String(error ?? "Unknown error");

      // Check for specific error types
      if (message.toLowerCase().includes("provider or integration unavailable")) {
        setShowLLMDialog(true);
        return false;
      }

      // Check if this is a guardrail violation (content policy error)
      const isGuardrailError = message.toLowerCase().includes("violates our usage policies") ||
                               message.toLowerCase().includes("prohibited content") ||
                               message.toLowerCase().includes("content policies");

      const errorId = Math.random().toString(36).slice(2);

      if (isGuardrailError) {
        // Display guardrail-specific error message
        setChatMessages((m) => [
          ...m,
          {
            id: errorId,
            role: "assistant",
            text: `⚠️ **Content Policy Violation**\n\n${message}\n\nPlease keep your messages focused on tool creation for your game environment.`
          }
        ]);
      } else {
        // Display generic error message
        setChatMessages((m) => [
          ...m,
          { id: errorId, role: "assistant", text: `Sorry, I encountered an error: ${message}` }
        ]);
      }

      return true; // generic errors still clear input since message was sent
    } finally {
      setIsTyping(false);
    }
  };

  if (loading) return <div className="text-muted-foreground">Loading…</div>;

  // Don't show main content until environment is selected for new tools
  if (isNew && showEnvironmentDialog) {
    return (
      <div className="w-full space-y-8 p-6 lg:p-8">
        <div className="w-full max-w-[95rem] mx-auto space-y-8">
          {/* Environment Selection Dialog will be shown */}
          {/* Environment Selection Dialog - shown before chat for new tools */}
          <Dialog open={showEnvironmentDialog} onOpenChange={(open) => {
            // Don't allow closing without selecting an environment
            if (!open && isNew) {
              return;
            }
            setShowEnvironmentDialog(open);
          }}>
            <DialogContent className="sm:max-w-2xl">
              <DialogHeader>
                <DialogTitle>Select Game Environment</DialogTitle>
                <DialogDescription>
                  Choose the game environment for this tool. This determines which game context the tool will operate in.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3 py-4">
                {getAvailableGameEnvironments().map((env) => {
                  const metadata = envMetadata?.[env];
                  if (!metadata) return null;
                  const theme = getEnvironmentTheme(env);
                  const EnvIcon = theme.icon;
                  return (
                    <div
                      key={env}
                      className={`relative p-4 border rounded-lg cursor-pointer transition-colors overflow-hidden ${
                        environment === env
                          ? 'border-brand-teal bg-brand-teal/5'
                          : 'border-border hover:border-brand-teal/50'
                      }`}
                      onClick={() => setEnvironment(env as GameEnvironment)}
                    >
                      {/* Environment-themed background gradient */}
                      <div
                        className="absolute inset-0 pointer-events-none"
                        style={{
                          background: `linear-gradient(to bottom right, ${theme.colors.primary}15, ${theme.colors.accent}10, transparent)`,
                        }}
                      />
                      <div className="relative z-10 flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${theme.iconColor} bg-background/50`}>
                          <EnvIcon className="h-5 w-5" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-semibold text-foreground">{metadata.displayName}</h4>
                          <p className="text-sm text-muted-foreground mt-1">{metadata.description}</p>
                        </div>
                        {environment === env && (
                          <div className="flex-shrink-0">
                            <div className="h-5 w-5 rounded-full bg-brand-teal flex items-center justify-center">
                              <Check className="h-3 w-3 text-white" />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              <DialogFooter>
                <Button
                  onClick={() => {
                    setShowEnvironmentDialog(false);
                  }}
                  disabled={!environment}
                >
                  Continue
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-8 p-6 lg:p-8">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header - matching the list page format */}
        <div className="relative mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="tools" opacity={0.20} />
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (returnTo) {
                      // If returning to agent editor, open the tools tab
                      if (returnTo.includes('/agents/')) {
                        navigate(returnTo, { state: { initialTab: 'tools' } });
                      } else {
                        navigate(returnTo);
                      }
                    } else {
                      navigate("/tools");
                    }
                  }}
                  className="bg-background/80 border shadow-sm hover:bg-accent hover:text-foreground"
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline">{returnTo ? 'Back' : 'Back to Tools'}</span>
                </Button>
                <div className="flex items-center gap-3 min-w-0">
                  <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 whitespace-nowrap overflow-hidden text-ellipsis max-w-[70vw] sm:max-w-none sm:whitespace-normal">
                    {isNew ? "Create New Tool" : `Edit ${displayName || "Tool"}`}
                  </h1>
                  {isSystemTool && !isNew && (
                    <span className="px-3 py-1 bg-blue-500/10 text-blue-500 text-sm font-medium rounded-lg border border-blue-500/20">
                      System Tool
                    </span>
                  )}
                </div>
              </div>
              <p className="hidden sm:block text-muted-foreground text-lg">
                {isNew ? "Create and test a new tool" : isSystemTool ? "View system tool (save to create your own copy)" : "Modify tool code and description"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Mobile Save icon on the right of the title */}
              <Button
                onClick={() => setShowSaveDialog(true)}
                className="md:hidden inline-flex bg-primary hover:bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                size="icon"
                aria-label={isSystemTool ? "Save As Copy" : "Save"}
              >
                <Save className="h-4 w-4" />
              </Button>
              {/* Desktop actions */}
              <Button
                onClick={() => setShowSaveDialog(true)}
                className="hidden md:inline-flex px-6 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary transition-colors font-medium shadow-lg shadow-primary/25"
              >
                <Save className="h-4 w-4" />
                <span className="hidden sm:inline ml-2">{isSystemTool ? "Save As Copy" : "Save Tool"}</span>
              </Button>
            </div>
          </div>
        </div>

      {/* Mobile toolbar with Save/Test + tabs; hidden on md+ */}
      <div className="md:hidden sticky top-0 z-30 mb-6 bg-background/95 backdrop-blur supports-backdrop-blur:bg-background/80 pointer-events-auto rounded-lg p-4 border">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
              <Code className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="font-medium text-lg text-foreground">Tool Editor</div>
              <div className="text-sm text-muted-foreground">Mobile</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Test button moved to bottom-left as floating action on mobile */}
            {/* Hidden always-present Test button for e2e reliability */}
            <button
              type="button"
              data-testid="open-test-dialog-fallback"
              className="hidden"
              onClick={openTestDialog}
              aria-hidden="true"
            />
          </div>
        </div>

        {/* Mobile tab selector */}
        <div className="flex items-center gap-2 bg-muted p-1 rounded-lg">
          <Button
            variant={mobileTab === 'chat' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1"
            onClick={() => setMobileTab('chat')}
            data-testid="m-tab-chat"
          >
            <MessageCircle className="h-4 w-4 mr-2" />
            Chat
          </Button>
          <Button
            variant={mobileTab === 'desc' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1"
            onClick={() => setMobileTab('desc')}
            data-testid="m-tab-desc"
          >
            <Edit3 className="h-4 w-4 mr-2" />
            Description
          </Button>
        </div>
      </div>

  {/* Main Content - separate containers with proper scrolling */}
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:min-h-[74vh]">
        {/* AI Chat Assistant */}
        <div className={`lg:col-span-2 ${mobileTab === 'chat' ? 'block' : 'hidden'} md:block`}>
          <div className="bg-card border-x border-t rounded-xl px-2 py-4 md:p-6 md:h-[74vh] h-[66svh] flex flex-col relative overflow-hidden">
            <EnvironmentBackground environment="tools" opacity={0.12} className="absolute inset-0 pointer-events-none" />
            <div className="relative z-10 flex flex-col h-full">
            <div className="flex items-center justify-between gap-3 mb-6">
              {/* LLM Selector replaces title */}
              <div className="flex-1 min-w-0">
                <LLMSelectorWrapper
                  context="tools"
                  compact
                  placeholder="Select a model"
                  className="w-full border-none"
                />
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {/* Clear chat: icon-only on mobile */}
                <Button
                  variant="outline"
                  size="icon"
                  className="sm:hidden"
                  onClick={() => setChatMessages([])}
                  aria-label="Clear chat"
                >
                  <X className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="hidden sm:inline-flex"
                  onClick={() => setChatMessages([])}
                  disabled={isTyping}
                >
                  Clear chat
                </Button>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden p-3 md:p-4">
              <ErrorBoundary>
                <VibeChat
                  messages={chatMessages}
                  onSend={onSendChat}
                  isTyping={isTyping}
                  onClearAll={() => setChatMessages([])}
                  hideHeader={true}
                  hideModelSelector={true}
                  className="h-full no-card-hover"
                  onUseCode={(code) => {
                    setCode(code);
                    const lastAssistantMessage = chatMessages.filter(m => m.role === 'assistant').pop();
                    if (lastAssistantMessage) {
                      const extractedDescription = extractFunctionDescription(lastAssistantMessage.text);
                      if (extractedDescription && !description.trim()) setDescription(extractedDescription);
                    }
                  }}

                  onTestJsonGenerated={handleTestJsonGenerated}
                  onShowLLMDialog={() => setShowLLMDialog(true)}
                  autoScroll={true}
                  onTestButtonClick={() => {
                    console.log('[DEBUG] Test button clicked');
                    console.log('[DEBUG] generatedTestJson exists:', !!generatedTestJson);
                    console.log('[DEBUG] generatedTestJson length:', generatedTestJson?.length || 0);
                    console.log('[DEBUG] generatedTestJson preview:', generatedTestJson?.substring(0, 100));

                    // If we already have generated test JSON, open the test dialog with it
                    if (generatedTestJson && generatedTestJson.trim()) {
                      console.log('[DEBUG] Using existing test JSON - opening dialog');
                      openTestDialog();
                      return true; // Handled - don't ask LLM again
                    }
                    // No test JSON yet - let the default behavior ask LLM to generate it
                    console.log('[DEBUG] No test JSON - will ask LLM to generate');
                    return false; // Let MessageContent send the prompt to generate test JSON
                  }}

                />
              </ErrorBoundary>
            </div>
            </div>
          </div>
        </div>

        {/* Mobile Description tab content */}
        <div className={`md:hidden ${mobileTab === 'desc' ? 'block' : 'hidden'}`}>
          <div className="bg-card border rounded-xl p-6 h-[60svh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-foreground text-xl font-semibold">Description</h3>
              {!isEditingDescription && (
                <Button variant="ghost" size="sm" onClick={handleEditDescription} className="text-muted-foreground hover:text-foreground">
                  <Edit3 className="h-4 w-4 mr-1" />
                  Edit
                </Button>
              )}
            </div>
            <div className={`flex-1 min-h-0 overflow-y-auto mt-4 scrollbar-stable pt-2 ${isEditingDescription ? '' : 'scrollbar-visible'}`}>
              {isEditingDescription ? (
                <div className="space-y-3 h-full flex flex-col min-h-0 p-3">
                  <Textarea
                    value={editingDescription}
                    onChange={(e) => setEditingDescription(e.target.value)}
                    className="text-sm resize-none flex-1 min-h-0 overflow-y-auto scrollbar-stable p-3"
                    placeholder="What does this tool do?"
                    autoFocus
                  />
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button variant="default" size="sm" onClick={handleSaveDescription}>
                      <Check className="h-4 w-4 mr-1" />
                      Save
                    </Button>
                    <Button variant="ghost" size="sm" onClick={handleCancelEditDescription}>
                      <X className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : description ? (
                <div className="text-sm leading-relaxed break-words whitespace-pre-wrap">
                  <MessageContent content={description} />
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleEditDescription}
                  className="text-muted-foreground hover:text-foreground border-dashed border hover:border-border w-full justify-start py-8 mt-2"
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  Add description...
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Right sidebar with Description and Test Tool */}
  <div className="hidden md:flex flex-col gap-6 h-[74vh]">
          {/* Description */}
          <div className="bg-card border rounded-xl p-6 flex-1 min-h-0 flex flex-col relative overflow-hidden">
            <EnvironmentBackground environment="tools" opacity={0.20} className="absolute inset-0 pointer-events-none" />
            <div className="relative z-10 flex flex-col h-full">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <h3 className="text-foreground text-xl font-semibold">Description</h3>
              {!isEditingDescription && (
                <Button variant="ghost" size="sm" onClick={handleEditDescription} className="text-muted-foreground hover:text-foreground">
                  <Edit3 className="h-4 w-4 mr-1" />
                  Edit
                </Button>
              )}
            </div>
            <div className={`flex-1 min-h-0 overflow-y-auto mt-4 scrollbar-stable pt-2 ${isEditingDescription ? "" : "scrollbar-visible"}`}>
              {isEditingDescription ? (
                <div className="space-y-3 h-full flex flex-col min-h-0 p-3">
                  <Textarea
                    value={editingDescription}
                    onChange={(e) => setEditingDescription(e.target.value)}
                    className="text-sm resize-none flex-1 min-h-0 overflow-y-auto scrollbar-stable p-3"
                    placeholder="What does this tool do?"
                    autoFocus
                  />
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button variant="default" size="sm" onClick={handleSaveDescription}>
                      <Check className="h-4 w-4 mr-1" />
                      Save
                    </Button>
                    <Button variant="ghost" size="sm" onClick={handleCancelEditDescription}>
                      <X className="h-4 w-4 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : description ? (
                <div className="text-sm leading-relaxed break-words whitespace-pre-wrap">
                  <MessageContent content={description} />
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleEditDescription}
                  className="text-muted-foreground hover:text-foreground border-dashed border hover:border-border w-full justify-start py-8 mt-2"
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  Add description...
                </Button>
              )}

            </div>
            </div>
          </div>

          {/* Test Tool */}
          <div className="hidden md:block bg-card border rounded-xl p-6 flex-shrink-0 mt-auto relative overflow-hidden">
            <EnvironmentBackground environment="tools" opacity={0.12} className="absolute inset-0 pointer-events-none" />
            <div className="relative z-10">
            <h3 className="text-foreground text-xl font-semibold mb-4">Test Tool</h3>
            <Button
              onClick={() => {
                // If we already have generated test JSON, open the test dialog with it
                if (generatedTestJson && generatedTestJson.trim()) {
                  console.log('[DEBUG] Test Tool button: Using existing test JSON');
                  openTestDialog();
                } else {
                  // No test JSON yet - ask LLM to generate it
                  console.log('[DEBUG] Test Tool button: No test JSON, asking LLM to generate');
                  const prompt = "Generate a complete test event JSON object for this tool. The JSON must include: 1) A 'state' field with a realistic game state, 2) A 'player_id' field if the tool uses it, 3) Any other parameters the tool expects. Analyze the tool's code carefully to ensure all data follows the exact format it validates (e.g., if it validates card formats like '2C', 'AH', 'KS', use that exact format). Return ONLY the complete event JSON object wrapped in ```json markers, nothing else.";
                  onSendChat(prompt, undefined, selectedModel ?? undefined);
                }
              }}
              disabled={isTyping}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/25"
              data-testid="open-test-dialog-code"
            >
              <FlaskConical className="h-4 w-4 mr-2" />
              Test Tool
            </Button>
            {!isNew && validationStatus !== "valid" && (
              <p className="mt-3 text-xs text-amber-400">
                {validationStatus === "pending" ? "Pending" : "Error"} — This tool must pass the Test Tool to become valid. Agents cannot use it until then.
              </p>
            )}
            </div>
          </div>
        </div>
      </div>

      {/* Code Editor panel removed; using modal instead */}

        <TestDialog
        open={showTestDialog}
        onOpenChange={(open) => {
          setShowTestDialog(open);
          // Don't clear generated JSON when dialog closes - keep it for reuse
        }}
        onRun={handleRun}
        running={running}
        logs={logs}
        status={status}
        initialEventJson={generatedTestJson}
        onAttemptFix={handleAttemptFix}
        environment={environment}
      />
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Save Tool</DialogTitle>
            <DialogDescription>Display name, description, and environment are required to save this tool.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label htmlFor="tool-name" className="block text-sm font-medium mb-1">Display Name</label>
              <Input id="tool-name" value={displayName} onChange={e=>setDisplayName(e.target.value)} placeholder="My Tool" />
            </div>
            <div>
              <label htmlFor="tool-environment" className="block text-sm font-medium mb-1">Environment</label>
              <Select value={environment} onValueChange={(value) => setEnvironment(value as GameEnvironment)} disabled={true}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an environment" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="texas_holdem">Texas Hold'em Poker</SelectItem>
                  <SelectItem value="chess">Chess</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                {isNew ? "Environment was selected when creating the tool" : "Environment cannot be changed for existing tools"}
              </p>
            </div>
            <div>
              <label htmlFor="tool-description" className="block text-sm font-medium mb-1">Description</label>
              <Textarea id="tool-description" value={description} onChange={e=>setDescription(e.target.value)} rows={4} placeholder="What does this tool do?" className="text-sm" />
            </div>
          </div>
          <DialogFooter className="flex gap-2 justify-end">
            <Button variant="outline" onClick={()=>setShowSaveDialog(false)}>Cancel</Button>

            <Button disabled={!displayName.trim() || !description.trim()} onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <LLMIntegrationDialog
        open={showLLMDialog}
        onOpenChange={(open) => {
          setShowLLMDialog(open);
          // After user configures integration, refresh the context to get the new model
          if (!open) {
            // The LLM context should automatically refresh when the dialog closes
            // due to the onIntegrationChange callback
          }
        }}
        onIntegrationChange={async () => {
          await refreshIntegrations();
        }}
      />

      </div>
    </div>
  );
};

export default ToolEditorPage;
