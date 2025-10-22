import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Save, Bot, Settings, BarChart3, Wrench, ArrowLeft, ChevronDown, Gamepad2, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PageBackground } from "@/components/common/layout/PageBackground";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";

import { DropdownMenu, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";



import { Badge } from "@/components/ui/badge";
import { useToasts } from "@/components/common/notifications/ToastProvider";
import { agentsService, type AgentResponse, type AgentVersionResponse, GameEnvironment } from "@/services/agentsService";
import { type AgentId, type AgentVersionId, type ToolId } from '@/types/ids';
import { api, type ModelSelection, LLMProvider } from "@/lib/api";

// Tab Components
import { AgentToolsTab } from "@/components/pages/agents/tabs/AgentToolsTab";
import { AgentInstructionsTab } from "@/components/pages/agents/tabs/AgentInstructionsTab";
import { AgentSettingsTab } from "@/components/pages/agents/tabs/AgentSettingsTab";
import { AgentStatisticsTab } from "@/components/pages/agents/tabs/AgentStatisticsTab";
import { AgentSetupDialog } from "@/components/pages/agents/dialogs/AgentSetupDialog";
import { AgentRunTab } from "@/components/pages/agents/tabs/AgentRunTab";

export const AgentEditorPage: React.FC = () => {
  const { id } = useParams();
  const isNew = id === undefined;
  const navigate = useNavigate();
  const location = useLocation();
  const { push } = useToasts();

  // Helper function to resolve LLM provider string to LLMProvider enum
  const resolveToLLMProvider = (provider: string | null | undefined): LLMProvider | null => {
    if (!provider) return null;

    const providerLower = provider.toLowerCase();
    switch (providerLower) {
      case 'openai': return LLMProvider.OPENAI;
      case 'anthropic': return LLMProvider.ANTHROPIC;
      case 'google': return LLMProvider.GOOGLE;
      case 'aws_bedrock': return LLMProvider.AWS_BEDROCK;
      default: return null;
    }
  };

  // Helper function to get default model for a provider (fast model)
  const getProviderDefaultModel = async (provider: LLMProvider): Promise<ModelSelection | null> => {
    try {
      const [availableModels, integrations] = await Promise.all([
        api.llmIntegrations.getAvailableModelsDetailed(),
        api.llmIntegrations.list()
      ]);

      const providerInfo = availableModels.find(p => p.provider === provider);
      if (!providerInfo || providerInfo.models.length === 0) return null;

      const integration = integrations.find(int => int.provider === provider);
      if (!integration) return null;

      // Use the first model as default (this would be the fast model)
      return {
        modelId: providerInfo.models[0].modelId,
        provider: provider,
        integrationId: integration.id
      };
    } catch (error) {
      console.error('Failed to get provider default model:', error);
      return null;
    }
  };

  // Agent and version state
  const [agent, setAgent] = useState<AgentResponse | null>(null);
  const [versions, setVersions] = useState<AgentVersionResponse[]>([]);
  const [activeVersion, setActiveVersion] = useState<AgentVersionResponse | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<AgentVersionId | null>(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [isSystemAgent, setIsSystemAgent] = useState(false);

  // Form state
  const [activeTab, setActiveTab] = useState<"profile" | "llm" | "tools" | "instructions" | "statistics" | "run">("profile");
  const [showSetupDialog, setShowSetupDialog] = useState(isNew);

  // Agent basic info
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [gameEnvironment, setGameEnvironment] = useState<GameEnvironment>(GameEnvironment.TEXAS_HOLDEM);
  const [autoBuy, setAutoBuy] = useState(true);
  const [autoReenter, setAutoReenter] = useState(false);
  const [isActive, setIsActive] = useState(true);

  // Avatar state
  const [currentAvatar, setCurrentAvatar] = useState<string | null>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  // Version fields
  const [systemPrompt, setSystemPrompt] = useState("");
  const [conversationInstructions, setConversationInstructions] = useState("");
  const [exitCriteria, setExitCriteria] = useState("");
  const [toolIds, setToolIds] = useState<ToolId[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider | null>(null);
  const [timeout, setTimeout] = useState(30);
  const [maxIterations, setMaxIterations] = useState(10);
  const [promptErrors, setPromptErrors] = useState<string[]>([]);

  useEffect(() => {
    if (!isNew && id) {
      loadAgent(id as AgentId);
    }
  }, [id, isNew]);

  // Respect navigation state to open a specific tab after redirects (e.g., after saving)
  useEffect(() => {
    const state = (location.state as any) || {};
    if (state.initialTab) {
      setActiveTab(state.initialTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // when user changes selectedVersionId, load that version's fields into form
  useEffect(() => {
    if (!agent || !selectedVersionId) return;
    const v = versions.find(v => v.id === selectedVersionId);
    if (!v) return;

    setActiveVersion(v);
    setSystemPrompt(v.systemPrompt);
    setConversationInstructions(v.conversationInstructions || "");
    setExitCriteria(v.exitCriteria || "");
    setToolIds(v.toolIds || []);

    // Set the provider (use fast_llm_provider as the primary provider)
    const provider = resolveToLLMProvider(v.fastLlmProvider || v.slowLlmProvider);
    setSelectedProvider(provider);

    setTimeout(v.timeout);
    setMaxIterations(v.maxIterations);
  }, [agent?.id, selectedVersionId, versions]);

  // Update auto reenter default when environment changes (only for new agents that haven't been manually set)
  useEffect(() => {
    if (isNew) {
      // Default to false for all environments
      setAutoReenter(false);
    }
  }, [gameEnvironment, isNew]);

  const loadAgent = async (agentId: AgentId) => {
    try {
      setLoading(true);
      const [agentData, versionsData, activeVersionData] = await Promise.all([
        agentsService.get(agentId),
        agentsService.getVersions(agentId),
        agentsService.getActiveVersion(agentId)
      ]);

      if (agentData) {
        setAgent(agentData);
        setName(agentData.name);
        setDescription(agentData.description || "");
        setGameEnvironment(agentData.gameEnvironment);
        setAutoBuy(agentData.autoBuy);
        setAutoReenter(agentData.autoReenter);
        setIsActive(agentData.isActive);
        setIsSystemAgent(agentData.isSystem);
        setCurrentAvatar(agentData.avatarUrl || null);
      }

      if (versionsData) {
        setVersions(versionsData);
      }

      const effectiveVersion = activeVersionData || (versionsData && versionsData[0]) || null;
      if (effectiveVersion) {
        setActiveVersion(effectiveVersion);
        setSelectedVersionId(effectiveVersion.id);
        setSystemPrompt(effectiveVersion.systemPrompt);
        setConversationInstructions(effectiveVersion.conversationInstructions || "");
        setExitCriteria(effectiveVersion.exitCriteria || "");
        setToolIds(effectiveVersion.toolIds || []);

        // Set the provider (use fast_llm_provider as the primary provider)
        const provider = resolveToLLMProvider(effectiveVersion.fastLlmProvider || effectiveVersion.slowLlmProvider);
        setSelectedProvider(provider);

        setTimeout(effectiveVersion.timeout);
        setMaxIterations(effectiveVersion.maxIterations);
      }
    } catch (error) {
      console.error("Failed to load agent:", error);
      navigate("/agents");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setPromptErrors([]);

      // Check for missing fields and auto-navigate to first tab with errors
      const validation = getValidationInfo();
      if (!validation.isValid || validation.hasPromptErrors) {
        // Navigate to first tab with missing fields
        if (validation.tabsWithErrors.length > 0) {
          setActiveTab(validation.tabsWithErrors[0] as any);

          // Show specific error message
          const errorMessages = [];
          if (validation.missingFields.length > 0) {
            errorMessages.push(`Missing required fields: ${validation.missingFields.map(f => f.label).join(', ')}`);
          }
          if (validation.hasPromptErrors) {
            errorMessages.push('System prompt has validation errors');
          }

          push({
            tone: "error",
            title: "Complete required fields",
            message: errorMessages.join('. ') + ". Please fill in the highlighted fields to save your agent."
          });
          setSaving(false);
          return;
        }
      }

      // Validate prompt on save only for new agents or when system prompt actually changed
      const shouldValidatePrompt = isNew || (activeVersion && systemPrompt.trim() !== activeVersion.systemPrompt.trim());
      if (shouldValidatePrompt) {
        const validation = await agentsService.validatePrompt({ prompt: systemPrompt, environment: gameEnvironment });
        if (!validation.valid) {
          setPromptErrors(validation.errors || ["Invalid prompt"]);
          setActiveTab("instructions");
          push({ tone: "error", title: "Prompt validation failed", message: (validation.errors && validation.errors[0]) || "Please fix the highlighted issues." });
          setSaving(false);
          return;
        }
      }

      if (isNew) {
        const newAgent = await agentsService.create({
          name,
          description: description || undefined,
          gameEnvironment: gameEnvironment,
          autoBuy: autoBuy,
          autoReenter: autoReenter,
          isActive: isActive,
        });

        // Get the default model for the selected provider
        const defaultModel = await getProviderDefaultModel(selectedProvider!);
        if (!defaultModel) {
          throw new Error('Failed to get default model for selected provider');
        }

        await agentsService.createVersion(newAgent.id, {
          systemPrompt: systemPrompt,
          conversationInstructions: conversationInstructions || undefined,
          exitCriteria: exitCriteria || undefined,
          toolIds: toolIds,
          slowLlmProvider: defaultModel.provider,
          fastLlmProvider: defaultModel.provider,
          slowLlmModel: defaultModel.modelId,
          fastLlmModel: defaultModel.modelId,
          timeout,
          maxIterations: maxIterations,
        });

        push({ tone: "success", title: "Agent created", message: "Your agent and its first version have been saved." });
        // If user initiated save from the Run tab, return to Run on the new route
        const navState = activeTab === "run" ? { state: { initialTab: "run" } } : undefined;
        navigate(`/agents/${newAgent.id}`, navState as any);
      } else if (agent && activeVersion && isSystemAgent) {
        // Clone system agent instead of updating
        console.log('Cloning system agent:', agent.id);
        const clonedAgent = await agentsService.clone(agent.id);
        console.log('Agent cloned successfully:', clonedAgent);
        push({ tone: "success", title: "Agent copied", message: "System agent has been copied to your account." });
        // Navigate to the cloned agent
        navigate(`/agents/${clonedAgent.id}`);
      } else if (agent && activeVersion) {
        // Update agent basics
        await agentsService.update(agent.id, {
          name,
          description: description || undefined,
          autoBuy: autoBuy,
          autoReenter: autoReenter,
          isActive: isActive,
        });

        // Compute diffs for version update
        const arraysEqual = (a: ToolId[] = [], b: ToolId[] = []) => (
          a.length === b.length && a.every((v, i) => v === b[i])
        );

        const updatePayload: any = {};
        // Version-defining fields: include only if changed
        if (systemPrompt !== activeVersion.systemPrompt) {
          updatePayload.systemPrompt = systemPrompt;
        }
        if ((conversationInstructions || "") !== (activeVersion.conversationInstructions || "")) {
          updatePayload.conversationInstructions = conversationInstructions;
        }
        if ((exitCriteria || "") !== (activeVersion.exitCriteria || "")) {
          updatePayload.exitCriteria = exitCriteria;
        }
        if (!arraysEqual(toolIds || [], activeVersion.toolIds || [])) {
          updatePayload.toolIds = toolIds;
        }

        // Configuration fields: include only if changed
        if (selectedProvider && selectedProvider !== (activeVersion as any).fastLlmProvider) {
          // Get the default model for the selected provider
          const defaultModel = await getProviderDefaultModel(selectedProvider);
          if (defaultModel) {
            updatePayload.fastLlmProvider = defaultModel.provider;
            updatePayload.fastLlmModel = defaultModel.modelId;
            updatePayload.slowLlmProvider = defaultModel.provider;
            updatePayload.slowLlmModel = defaultModel.modelId;
          }
        }
        if (timeout !== activeVersion.timeout) {
          updatePayload.timeout = timeout;
        }
        if (maxIterations !== activeVersion.maxIterations) {
          updatePayload.maxIterations = maxIterations;
        }

        // Only call update if there is something to update
        if (Object.keys(updatePayload).length > 0) {
          await agentsService.updateVersion(agent.id, activeVersion.id, updatePayload as any);
        }

        await loadAgent(agent.id);
        push({ tone: "success", title: "Agent updated", message: "Changes to your agent have been saved." });
      }
    } catch (error) {
      console.error("Failed to save agent:", error);

      // Extract error message from API response
      const errorMessage = error instanceof Error ? error.message : "We couldn't save your changes. Please try again.";

      // Check if this is a guardrail violation (content policy error)
      const isGuardrailError = errorMessage.toLowerCase().includes("prohibited content") ||
                               errorMessage.toLowerCase().includes("violates our policies") ||
                               errorMessage.toLowerCase().includes("content policies");

      if (isGuardrailError) {
        push({
          tone: "error",
          title: "Content Policy Violation",
          message: errorMessage || "Your agent instructions contain content that violates our policies. Please revise and try again."
        });
      } else {
        push({
          tone: "error",
          title: "Save failed",
          message: errorMessage
        });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSetupComplete = (setupData: { name: string; description: string; gameEnvironment: GameEnvironment }) => {
    setName(setupData.name);
    setDescription(setupData.description);
    setGameEnvironment(setupData.gameEnvironment);
    setShowSetupDialog(false);
    setActiveTab("profile"); // Start with profile tab after setup
  };

  const getValidationInfo = () => {
    const missingFields = [];
    const tabsWithErrors = [];

    if (!name.trim()) {
      missingFields.push({ field: 'name', tab: 'profile', label: 'Agent Name' });
      tabsWithErrors.push('profile');
    }

    if (!systemPrompt.trim()) {
      missingFields.push({ field: 'systemPrompt', tab: 'instructions', label: 'System Prompt' });
      tabsWithErrors.push('instructions');
    }

    if (!selectedProvider) {
      missingFields.push({ field: 'provider', tab: 'llm', label: 'LLM Provider' });
      tabsWithErrors.push('llm');
    }

    const uniqueTabs = [...new Set(tabsWithErrors)];

    return {
      isValid: missingFields.length === 0,
      missingFields,
      tabsWithErrors: uniqueTabs,
      toolCountValid: toolIds.length <= 10,
      hasPromptErrors: promptErrors.length > 0
    };
  };

  const canSave = () => {
    const validation = getValidationInfo();
    return validation.isValid && !validation.hasPromptErrors;
  };

  // Derive missing info for tabs and field hints
  const { profileMissingCount, settingsMissingCount, instructionsMissingCount, hasPromptErrors, validationInfo } = React.useMemo(() => {
    const profileMissing = name.trim() ? 0 : 1;
    const settingsMissing = selectedProvider ? 0 : 1;
    const instructionsMissing = systemPrompt.trim() ? 0 : 1;
    const validation = getValidationInfo();
    return {
      profileMissingCount: profileMissing,
      settingsMissingCount: settingsMissing,
      instructionsMissingCount: instructionsMissing,
      hasPromptErrors: (promptErrors && promptErrors.length > 0) || false,
      validationInfo: validation
    };
  }, [name, selectedProvider, systemPrompt, promptErrors, toolIds]);

  // Avatar handlers
  const handleAvatarUpload = async (
    file: File,
    cropData?: { x: number; y: number; size: number; scale: number }
  ) => {
    if (!id) return;

    setUploadingAvatar(true);
    try {
      const response = await api.avatars.uploadAgentAvatar(id, file, cropData);
      setCurrentAvatar(response.avatarUrl); // using camelCase from api.ts
      push({ title: "Success", message: "Agent avatar updated successfully", tone: "success" });
    } catch (e) {
      console.error("Failed to upload agent avatar", e);
      const msg = e instanceof Error ? e.message : "Failed to upload avatar";
      push({ title: "Error", message: msg, tone: "error" });
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleAvatarRemove = async () => {
    if (!id) return;

    setUploadingAvatar(true);
    try {
      const response = await api.avatars.resetAgentAvatar(id);
      setCurrentAvatar(response.avatarUrl);
      push({ title: "Success", message: "Agent avatar reset successfully", tone: "success" });
    } catch (e) {
      console.error("Failed to reset agent avatar", e);
      const msg = e instanceof Error ? e.message : "Failed to reset avatar";
      push({ title: "Error", message: msg, tone: "error" });
    } finally {
      setUploadingAvatar(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading agent...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-hidden">
      <PageBackground environment={gameEnvironment} className="h-full overflow-hidden">
        {/* Show main content only if setup is complete or editing existing agent */}
        {!showSetupDialog ? (
          <div className="w-full h-full overflow-hidden flex flex-col">
            {/* Header - fixed at top */}
            <div className="relative shrink-0 flex items-center justify-between bg-card/30 backdrop-blur-sm border-b border-border/50 px-3 py-2 md:px-6 md:py-3">
              {/* Subtle environment art behind header */}
              {gameEnvironment && (
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                  <EnvironmentBackground environment={gameEnvironment} opacity={0.20} />
                </div>
              )}
              <div className="flex items-center gap-4 flex-1 min-w-0 relative z-10">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/agents")}
                  className="bg-background/80 border shadow-sm hover:bg-accent hover:text-foreground rounded-lg"
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline">Back to Agents</span>
                </Button>
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <h1 className="text-xl sm:text-3xl font-bold text-foreground truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal">
                      {isNew ? "Create New Agent" : `Edit ${name || "Agent"}`}
                    </h1>
                    {isSystemAgent && !isNew && (
                      <span className="px-3 py-1 bg-blue-500/10 text-blue-500 text-sm font-medium rounded-lg border border-blue-500/20">
                        System Agent
                      </span>
                    )}
                  </div>
                  <p className="hidden sm:block text-muted-foreground text-sm">
                    {isNew ? "Configure your AI agent for automated gameplay" : isSystemAgent ? "View system agent (save to create your own copy)" : "Modify agent settings and behavior"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 relative z-10">
                {!isNew && (
                  <div className="hidden md:flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Version</span>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-lg bg-secondary/60 border-border text-foreground hover:bg-muted min-w-[72px] px-3 py-1.5 h-8"
                        >
                          {(() => {
                            const v = versions.find(v => v.id === selectedVersionId) || activeVersion;
                            return v ? `v${v.versionNumber}` : "Version";
                          })()}
                          <ChevronDown className="ml-1 h-3.5 w-3.5 opacity-70" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start" className="min-w-[8rem]">
                        <DropdownMenuRadioGroup
                          value={(selectedVersionId ?? "") as string}
                          onValueChange={(val) => setSelectedVersionId(val as AgentVersionId)}
                        >
                          {versions.map((v) => (
                            <DropdownMenuRadioItem key={v.id} value={v.id}>
                              {`v${v.versionNumber}`}
                              {activeVersion && v.id === activeVersion.id ? "  (active)" : ""}
                            </DropdownMenuRadioItem>
                          ))}
                        </DropdownMenuRadioGroup>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    {activeVersion && selectedVersionId === activeVersion.id ? (
                      null
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          if (!agent || !selectedVersionId) return;
                          const updated = await agentsService.activateVersion(agent.id, selectedVersionId);
                          setActiveVersion(updated);
                          setSelectedVersionId(updated.id);
                          const fresh = await agentsService.getVersions(agent.id);
                          setVersions(fresh);
                        }}
                        className="text-foreground border-border hover:bg-muted rounded-lg"
                      >
                        Activate
                      </Button>
                    )}
                  </div>
                )}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        onClick={handleSave}
                        disabled={!canSave() || saving}
                        className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary transition-colors font-medium shadow-lg shadow-primary/25"
                        title={!canSave() ? "Complete the highlighted fields before saving" : undefined}
                      >
                        <Save className="h-4 w-4" />
                        <span className="hidden sm:inline ml-2">{saving ? "Saving..." : isSystemAgent ? "Save As Copy" : "Save Agent"}</span>
                      </Button>
                    </TooltipTrigger>
                    {!canSave() && (
                      <TooltipContent side="top" className="max-w-md sm:bottom-auto sm:top-full mt-2 sm:mt-0 sm:mb-2">
                        <div className="space-y-2">
                          <p className="font-medium text-sm">Complete these required fields:</p>
                          <div className="space-y-1">
                            {validationInfo.missingFields.map((field, index) => (
                              <div key={index} className="flex items-center gap-2 text-sm">
                                <span className="w-2 h-2 bg-destructive rounded-full"></span>
                                <span>{field.label}</span>
                                <span className="text-muted-foreground text-xs">({field.tab})</span>
                              </div>
                            ))}
                            {validationInfo.hasPromptErrors && (
                              <div className="flex items-center gap-2 text-sm">
                                <span className="w-2 h-2 bg-destructive rounded-full"></span>
                                <span>Fix prompt validation errors</span>
                                <span className="text-muted-foreground text-xs">(instructions)</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </TooltipContent>
                    )}
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>

            {/* Main Content - Tabs with fixed height */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="w-full h-full flex flex-col overflow-hidden">
                {/* Sticky Tabs Header */}
                <TabsList className="grid w-full grid-cols-6 shrink-0 h-14 p-1 bg-transparent border-b border-border/50 rounded-none sticky top-2 md:top-3 z-20">
                  <TabsTrigger
                    value="profile"
                    className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
                  >
                    <User className="h-6 w-6 sm:h-5 sm:w-5 text-purple-500 group-data-[state=active]:text-primary-foreground" />
                    <span className="hidden sm:inline">Profile</span>
                    {profileMissingCount > 0 && (
                      <Badge variant="destructive" className="ml-2 text-xs">{profileMissingCount}</Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger
                    value="llm"
                    className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
                  >
                    <Settings className="h-6 w-6 sm:h-5 sm:w-5 text-green-500 group-data-[state=active]:text-primary-foreground" />
                    <span className="hidden sm:inline">LLM</span>
                    {settingsMissingCount > 0 && (
                      <Badge variant="destructive" className="ml-2 text-xs">{settingsMissingCount}</Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger
                    value="instructions"
                    className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
                  >
                    <Bot className="h-6 w-6 sm:h-5 sm:w-5 text-cyan-500 group-data-[state=active]:text-primary-foreground" />
                    <span className="hidden sm:inline">Instructions</span>
                    {hasPromptErrors ? (
                      <span className="ml-2 h-2 w-2 rounded-full bg-destructive" />
                    ) : (
                      instructionsMissingCount > 0 && (
                        <Badge variant="destructive" className="ml-2 text-xs">{instructionsMissingCount}</Badge>
                      )
                    )}
                  </TabsTrigger>
                  <TabsTrigger
                    value="tools"
                    className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
                  >
                    <Wrench className="h-6 w-6 sm:h-5 sm:w-5 text-orange-500 group-data-[state=active]:text-primary-foreground" />
                    <span className="hidden sm:inline">Tools</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="run"
                    className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
                  >
                    <Gamepad2 className="h-6 w-6 sm:h-5 sm:w-5 text-indigo-500 group-data-[state=active]:text-primary-foreground" />
                    <span className="hidden sm:inline">Playground</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="statistics"
                    className="flex group items-center gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-lg border border-transparent data-[state=active]:border-primary/20"
                  >
                    <BarChart3 className="h-6 w-6 sm:h-5 sm:w-5 text-yellow-500 group-data-[state=active]:text-primary-foreground" />
                    <span className="hidden sm:inline">Statistics</span>
                  </TabsTrigger>
                </TabsList>

                {/* Tab Content - Fixed height with scrollable content */}
                <div className="relative flex-1 min-h-0 overflow-y-auto">
                  <EnvironmentBackground environment={gameEnvironment} opacity={0.15} className="absolute inset-0 pointer-events-none" />

                  <TabsContent value="profile" className="min-h-full px-3 py-4 md:px-6 md:py-6 data-[state=inactive]:hidden">
                    <AgentSettingsTab
                      name={name}
                      description={description}
                      gameEnvironment={gameEnvironment}
                      selectedProvider={null}
                      autoReenter={autoReenter}
                      maxIterations={maxIterations}
                      isNew={isNew}
                      currentAvatar={currentAvatar}
                      uploadingAvatar={uploadingAvatar}
                      onNameChange={setName}
                      onDescriptionChange={setDescription}
                      onGameEnvironmentChange={setGameEnvironment}
                      onProviderChange={() => {}} // Provider handled in llm tab
                      onAutoReenterChange={setAutoReenter}
                      onMaxIterationsChange={setMaxIterations}
                      onAvatarRemove={handleAvatarRemove}
                      validationErrors={validationInfo.missingFields.filter(f => f.tab === 'profile')}
                      title="Agent Details"
                      showProvider={false}
                      showAutoReenter={false}
                      showMaxIterations={false}
                      onAvatarUpload={async (file: File, cropData?: { x: number; y: number; size: number; scale: number }) => await handleAvatarUpload(file, cropData)}
                    />
                  </TabsContent>

                  <TabsContent value="llm" className="min-h-full px-3 py-4 md:px-6 md:py-6 data-[state=inactive]:hidden">
                    <AgentSettingsTab
                      name=""
                      description=""
                      gameEnvironment={gameEnvironment}
                      selectedProvider={selectedProvider}
                      autoReenter={autoReenter}
                      maxIterations={maxIterations}
                      isNew={isNew}
                      currentAvatar={null}
                      uploadingAvatar={uploadingAvatar}
                      onNameChange={() => {}} // Name handled in profile tab
                      onDescriptionChange={() => {}} // Description handled in profile tab
                      onGameEnvironmentChange={setGameEnvironment}
                      onProviderChange={setSelectedProvider}
                      onAutoReenterChange={setAutoReenter}
                      onMaxIterationsChange={setMaxIterations}
                      onAvatarUpload={async () => {}} // Avatar handled in profile tab
                      onAvatarRemove={async () => {}} // Avatar handled in profile tab
                      validationErrors={validationInfo.missingFields.filter(f => f.tab === 'llm')}
                      title="Agent Configuration"
                      showProvider={true}
                      showAutoReenter={true}
                      showMaxIterations={true}
                      showBasicSettings={false}
                    />
                  </TabsContent>

                  <TabsContent value="instructions" className="min-h-full px-3 py-4 md:px-6 md:py-6 data-[state=inactive]:hidden">
                    <AgentInstructionsTab
                      systemPrompt={systemPrompt}
                      conversationInstructions={conversationInstructions}
                      exitCriteria={exitCriteria}
                      gameEnvironment={gameEnvironment}
                      onSystemPromptChange={setSystemPrompt}
                      onConversationInstructionsChange={setConversationInstructions}
                      onExitCriteriaChange={setExitCriteria}
                      externalErrors={promptErrors}
                      hasSystemPromptError={validationInfo.missingFields.some(f => f.field === 'systemPrompt')}
                    />
                  </TabsContent>

                  <TabsContent value="tools" className="min-h-full px-3 py-4 md:px-6 md:py-6 data-[state=inactive]:hidden">
                    <AgentToolsTab
                      toolIds={toolIds}
                      onToolIdsChange={setToolIds}
                      environment={gameEnvironment}
                    />
                  </TabsContent>

                  <TabsContent value="run" className="min-h-full px-3 py-4 md:px-6 md:py-6 data-[state=inactive]:hidden">
                    {agent && activeVersion ? (
                      <AgentRunTab agentId={agent.id} activeVersion={activeVersion} gameEnvironment={gameEnvironment} />
                    ) : (
                      <div className="text-center py-12" data-testid="run-save-required">
                        <Gamepad2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-60" />
                        <h3 className="text-lg font-semibold text-foreground mb-2">Save required to start</h3>
                        <p className="text-muted-foreground mb-6">Please save your agent before starting the playground.</p>
                        <div className="flex items-center justify-center gap-3">
                          <Button
                            onClick={handleSave}
                            disabled={!canSave() || saving}
                            className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium shadow-lg shadow-primary/25"
                            data-testid="run-save-agent-button"
                          >
                            <Save className="h-4 w-4" />
                            <span className="ml-2">{saving ? "Saving..." : "Save Agent"}</span>
                          </Button>
                          {!canSave() && (
                            <Button
                              variant="outline"
                              onClick={() => setActiveTab("instructions")}
                              data-testid="run-fix-required-fields"
                              className="rounded-lg"
                            >
                              Go to Instructions
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="statistics" className="min-h-full px-3 py-4 md:px-6 md:py-6 data-[state=inactive]:hidden">
                    {agent ? (
                      <AgentStatisticsTab agentId={agent.id} environment={gameEnvironment} />
                    ) : (
                      <div className="text-center py-12">
                        <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <h3 className="text-lg font-semibold text-foreground mb-2">Statistics Unavailable</h3>
                        <p className="text-muted-foreground">Create and save the agent first to view statistics.</p>
                      </div>
                    )}
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-white mb-2">Setup Required</h2>
              <p className="text-gray-400">Complete the setup dialog to configure your AI agent.</p>
            </div>
          </div>
        )}

        {/* Setup Dialog for new agents */}
        <AgentSetupDialog
          open={showSetupDialog}
          onOpenChange={setShowSetupDialog}
          onComplete={handleSetupComplete}
          onCancel={() => navigate("/agents")}
        />
      </PageBackground>
    </div>
  );
};

export default AgentEditorPage;
