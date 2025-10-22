import React, { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Settings, Plus, ChevronDown, Search, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  api,
  ProviderModelInfo,
  SelectableModel,
  ModelSelection,
} from "@/lib/api";
import { LLMIntegrationDialog } from "./LLMIntegrationDialog";
import { ProviderIcon } from "@/components/llm/ProviderIcon";
import { useLLM } from "@/contexts/LLMContext";
import { type LLMIntegrationId } from "@/types/ids";

interface EnhancedLLMModelSelectorProps {
  // Preferred: model-based selection
  selectedModel?: ModelSelection | null;
  onSelectionChange?: (selection: ModelSelection | null) => void;
  // Back-compat: integration-id based selection
  selectedIntegrationId?: LLMIntegrationId | null;
  onIntegrationIdChange?: (integrationId: LLMIntegrationId | null) => void;
  className?: string;
  compact?: boolean;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  showSettings?: boolean;
}

export const EnhancedLLMModelSelector: React.FC<EnhancedLLMModelSelectorProps> = ({
  selectedModel,
  onSelectionChange,
  selectedIntegrationId,
  onIntegrationIdChange,
  className = "",
  compact = false,
  label,
  placeholder = "Select a model",
  disabled = false,
  showSettings = true
}) => {
  // Use LLM context for integrations
  const { integrations, loading: contextLoading, refreshIntegrations, defaultIntegration } = useLLM();

  const [availableModels, setAvailableModels] = useState<ProviderModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  // Local selection to support integration-id only mode while still allowing model-level highlight changes
  const [localSelection, setLocalSelection] = useState<ModelSelection | null>(null);

  // Load available models
  const loadAvailableModels = async () => {
    setLoading(true);
    try {
      const modelsData = await api.llmIntegrations.getAvailableModelsDetailed();
      setAvailableModels(modelsData);
    } catch (error) {
      console.error("Failed to load available models:", error);
    } finally {
      setLoading(false);
    }
  };

  // Load available models on mount
  useEffect(() => {
    loadAvailableModels();
  }, []);

  const getProviderName = (provider: string) => {
    switch (provider) {
      case 'openai': return 'OpenAI';
      case 'anthropic': return 'Anthropic';
      case 'google': return 'Google';
      case 'aws_bedrock': return 'AWS Bedrock';
      default: return provider;
    }
  };

  // Create selectable models from active integrations
  const selectableModels: SelectableModel[] = useMemo(() => {
    const activeIntegrations = integrations.filter(i => i.isActive);
    const models: SelectableModel[] = [];

    activeIntegrations.forEach(integration => {
      const providerModels = availableModels.find(p => p.provider === integration.provider);
      if (providerModels) {
        providerModels.models.forEach(model => {
          models.push({
            modelId: model.modelId,
            displayName: model.displayName,
            provider: integration.provider,
            providerName: getProviderName(integration.provider),
            integrationId: integration.id,
            description: model.description,
            contextWindow: model.contextWindow,
            supportsTools: model.supportsTools,
            supportsVision: model.supportsVision,
            inputPricePer1m: model.inputPricePer1m,
            outputPricePer1m: model.outputPricePer1m,
          });
        });
      }
    });

    return models;
  }, [integrations, availableModels]);

  // Auto-select default or first model if none selected and no local selection exists
  // Only run this after a delay to ensure parent state has time to load
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!selectedModel && !localSelection && selectableModels.length > 0) {
        const preferred = defaultIntegration
          ? selectableModels.find(m => m.integrationId === defaultIntegration.id)
          : null;
        const pick = preferred || selectableModels[0];
        const selection: ModelSelection = {
          modelId: pick.modelId,
          provider: pick.provider,
          integrationId: pick.integrationId,
        };
        setLocalSelection(selection);
        onSelectionChange?.(selection);
      }
    }, 100); // Small delay to let parent state settle

    return () => clearTimeout(timer);
  }, [selectedModel, localSelection, selectableModels, defaultIntegration]);

  // Filter models based on search query
  const filteredModels = useMemo(() => {
    if (!searchQuery.trim()) return selectableModels;

    const query = searchQuery.toLowerCase();
    return selectableModels.filter(model =>
      model.displayName.toLowerCase().includes(query) ||
      model.modelId.toLowerCase().includes(query) ||
      model.providerName.toLowerCase().includes(query) ||
      model.description.toLowerCase().includes(query)
    );
  }, [selectableModels, searchQuery]);

  const handleModelSelect = (model: SelectableModel) => {
    const selection: ModelSelection = {
      modelId: model.modelId,
      provider: model.provider,
      integrationId: model.integrationId
    };
    // Keep local selection so highlight updates even if parent only controls integration-id
    setLocalSelection(selection);
    // Fire callbacks
    onSelectionChange?.(selection);
    onIntegrationIdChange?.(model.integrationId);
    // Optimistically close and clear search
    setDropdownOpen(false);
    setSearchQuery("");
  };

  const handleIntegrationChange = () => {
    refreshIntegrations();
    loadAvailableModels();
  };

  // Determine the current selection. Prefer selectedModel when provided; fallback to integration id.
  const selectedModelInfo = useMemo(() => {
    const source = selectedModel || localSelection || null;

    if (source) {
      const found = selectableModels.find(m =>
        m.modelId === source.modelId &&
        m.provider === source.provider &&
        m.integrationId === source.integrationId
      );
      return found || null;
    }
    if (selectedIntegrationId != null) {
      // Fallback to first model of this integration when only integration id is controlled by parent
      return selectableModels.find(m => m.integrationId === selectedIntegrationId) || null;
    }
    return null;
  }, [selectedModel, localSelection, selectedIntegrationId, selectableModels]);

  // If the current selection refers to a deleted or inactive integration, clear it
  // Only do this after models have loaded to avoid clearing valid selections during initial load
  useEffect(() => {
    if (selectedModel && !selectedModelInfo && selectableModels.length > 0 && !loading && !contextLoading) {
      onSelectionChange && onSelectionChange(null);
      onIntegrationIdChange && onIntegrationIdChange(null);
    }
  }, [selectedModel, selectedModelInfo, selectableModels.length, loading, contextLoading, onSelectionChange, onIntegrationIdChange]);

  if (compact) {
    return (
      <>
        <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              disabled={disabled || loading || contextLoading}
              className={`justify-between text-left ${className}`}
              data-testid="llm-model-trigger"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {selectedModelInfo ? (
                  <>
                    <div className="text-xs flex-shrink-0 flex items-center gap-1">
                      <ProviderIcon provider={selectedModelInfo.provider} size={12} className="h-3 w-3" />
                      {selectedModelInfo.providerName}
                    </div>
                    <span className="truncate text-sm">{selectedModelInfo.displayName}</span>
                  </>
                ) : (
                  <span className="text-muted-foreground text-sm">{placeholder}</span>
                )}
              </div>
              <ChevronDown className="h-4 w-4 flex-shrink-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[400px] max-w-[calc(100vw-1rem)] no-card-hover">
            <div className="p-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search models..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    // Prevent dropdown from closing when typing
                    e.stopPropagation();
                  }}
                  data-adornment-start="true"
                  className=""
                />
              </div>
            </div>

            {filteredModels.length > 0 ? (
              <>
                <div className="max-h-[300px] overflow-y-auto">
                  {filteredModels.map((model) => (
                    <DropdownMenuItem
                      key={`${model.provider}-${model.modelId}-${model.integrationId}`}
                      onClick={() => handleModelSelect(model)}
                      className="flex items-center justify-between p-3 cursor-pointer"
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <div className="text-xs flex-shrink-0 flex items-center gap-1">
                          <ProviderIcon provider={model.provider} size={12} className="h-3 w-3" />
                          {model.providerName}
                        </div>
                        <div className="flex flex-col min-w-0 flex-1">
                          <span className="text-sm font-medium truncate">{model.displayName}</span>
                          <span className="text-xs text-muted-foreground truncate">{model.description}</span>
                        </div>
                      </div>
                      {selectedModelInfo &&
                       selectedModelInfo.modelId === model.modelId &&
                       selectedModelInfo.provider === model.provider &&
                       selectedModelInfo.integrationId === model.integrationId && (
                        <Check className="h-4 w-4 text-primary" />
                      )}
                    </DropdownMenuItem>
                  ))}
                </div>

                {showSettings && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setSettingsOpen(true)}
                      className="flex items-center gap-2 p-3"
                    >
                      <Settings className="h-4 w-4" />
                      <span>Manage Integrations</span>
                    </DropdownMenuItem>
                  </>
                )}
              </>
            ) : (
              <div className="p-4 text-center">
                {searchQuery ? (
                  <p className="text-muted-foreground text-sm">No models found matching "{searchQuery}"</p>
                ) : integrations.length === 0 ? (
                  <>
                    <p className="text-muted-foreground text-sm mb-3">No LLM integrations configured</p>
                    <Button
                      variant="outline"
                      onClick={() => setSettingsOpen(true)}
                      className="flex items-center gap-2"
                      size="sm"
                      data-testid="add-integration-button"
                    >
                      <Plus className="h-4 w-4" />
                      Add Integration
                    </Button>
                  </>
                ) : (
                  <p className="text-muted-foreground text-sm">No active integrations found</p>
                )}
              </div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {showSettings && (
          <LLMIntegrationDialog
            open={settingsOpen}
            onOpenChange={setSettingsOpen}
            onIntegrationChange={handleIntegrationChange}
          />
        )}
      </>
    );
  }

  // Full layout for non-compact mode
  return (
    <div className={`space-y-4 ${className}`}>
      {label && <Label className="text-base font-medium">{label}</Label>}

      {filteredModels.length > 0 ? (
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="Search models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                // Prevent any parent components from handling key events
                e.stopPropagation();
              }}
              data-adornment-start="true"
              className=""
            />
          </div>

          <div className="grid gap-2 max-h-[400px] overflow-y-auto scrollbar-stable pt-2 pr-1">
            {filteredModels.map((model) => (
              <div
                key={`${model.provider}-${model.modelId}-${model.integrationId}`}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedModelInfo &&
                  selectedModelInfo.modelId === model.modelId &&
                  selectedModelInfo.provider === model.provider &&
                  selectedModelInfo.integrationId === model.integrationId
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/50"
                }`}
                onClick={() => handleModelSelect(model)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="flex-shrink-0 flex items-center gap-1">
                      <ProviderIcon provider={model.provider} size={16} className="h-4 w-4" />
                      {model.providerName}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-sm truncate">{model.displayName}</p>
                      <p className="text-xs text-muted-foreground truncate">{model.description}</p>
                      <div className="flex items-center gap-4 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {model.contextWindow.toLocaleString()} tokens
                        </span>

                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {selectedModelInfo &&
                     selectedModelInfo.modelId === model.modelId &&
                     selectedModelInfo.provider === model.provider &&
                     selectedModelInfo.integrationId === model.integrationId && (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-6 border border-dashed rounded-lg">
          {searchQuery ? (
            <p className="text-muted-foreground mb-3">No models found matching "{searchQuery}"</p>
          ) : integrations.length === 0 ? (
            <>
              <p className="text-muted-foreground mb-3">No LLM integrations configured</p>
              <Button
                variant="outline"
                onClick={() => setSettingsOpen(true)}
                className="flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Add Integration
              </Button>
            </>
          ) : (
            <p className="text-muted-foreground">No active integrations found</p>
          )}
        </div>
      )}

      {showSettings && (
        <LLMIntegrationDialog
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          onIntegrationChange={handleIntegrationChange}
        />
      )}
    </div>
  );
};

export default EnhancedLLMModelSelector;
