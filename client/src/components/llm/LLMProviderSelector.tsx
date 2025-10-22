import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Settings, Plus, ChevronDown, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { LLMProvider } from "@/lib/api";
import { LLMIntegrationDialog } from "./LLMIntegrationDialog";
import { ProviderIcon } from "@/components/llm/ProviderIcon";
import { useLLM } from "@/contexts/LLMContext";

interface LLMProviderSelectorProps {
  selectedProvider?: LLMProvider | null;
  onProviderChange?: (provider: LLMProvider | null) => void;
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  showSettings?: boolean;
}

export const LLMProviderSelector: React.FC<LLMProviderSelectorProps> = ({
  selectedProvider,
  onProviderChange,
  className = "",
  placeholder = "Select a provider",
  disabled = false,
  showSettings = true
}) => {
  const { integrations, loading: contextLoading, refreshIntegrations } = useLLM();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const getProviderName = (provider: LLMProvider) => {
    switch (provider) {
      case LLMProvider.OPENAI: return 'OpenAI';
      case LLMProvider.ANTHROPIC: return 'Anthropic';
      case LLMProvider.GOOGLE: return 'Google';
      case LLMProvider.AWS_BEDROCK: return 'AWS Bedrock';
      default: return provider;
    }
  };

  // Get unique providers from active integrations
  const availableProviders = Array.from(
    new Set(
      integrations
        .filter(integration => integration.isActive)
        .map(integration => integration.provider)
    )
  );

  // Auto-select first available provider if none selected (only on initial load)
  useEffect(() => {
    if (!selectedProvider && availableProviders.length > 0) {
      onProviderChange?.(availableProviders[0]);
    }
  }, [availableProviders.length]); // Only trigger when count changes, not the entire array

  const handleProviderSelect = (provider: LLMProvider) => {
    onProviderChange?.(provider);
    setDropdownOpen(false);
  };

  const handleIntegrationChange = () => {
    refreshIntegrations();
  };

  const selectedProviderName = selectedProvider ? getProviderName(selectedProvider) : null;

  return (
    <>
      <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            disabled={disabled || contextLoading}
            className={`justify-between text-left w-full ${className}`}
            data-testid="llm-provider-trigger"
          >
            <div className="flex items-center gap-2 min-w-0 flex-1">
              {selectedProvider ? (
                <>
                  <ProviderIcon provider={selectedProvider} size={16} className="h-4 w-4" />
                  <span className="truncate">{selectedProviderName}</span>
                </>
              ) : (
                <span className="text-muted-foreground">{placeholder}</span>
              )}
            </div>
            <ChevronDown className="h-4 w-4 flex-shrink-0" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="min-w-[250px]">
          {availableProviders.length > 0 ? (
            <>
              {availableProviders.map((provider) => (
                <DropdownMenuItem
                  key={provider}
                  onClick={() => handleProviderSelect(provider)}
                  className="flex items-center justify-between p-3 cursor-pointer"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <ProviderIcon provider={provider} size={16} className="h-4 w-4 flex-shrink-0" />
                    <span className="truncate">{getProviderName(provider)}</span>
                  </div>
                  {selectedProvider === provider && (
                    <Check className="h-4 w-4 text-primary flex-shrink-0 ml-2" />
                  )}
                </DropdownMenuItem>
              ))}

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
              {integrations.length === 0 ? (
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
};

export default LLMProviderSelector;