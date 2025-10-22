import { useEffect, useRef } from 'react';
import { LLMIntegrationResponse, ModelSelection } from '@/lib/api';
import { useLLM, useToolsLLM, useAgentLLM, useGlobalLLM } from '@/contexts/LLMContext';

export type LLMSelectionContext = 'tools' | 'agents' | 'global';

interface UseLLMSelectionOptions {
  context?: LLMSelectionContext;
  autoLoad?: boolean;
}

interface UseLLMSelectionReturn {
  // New model-based selection
  selectedModel: ModelSelection | null;
  setSelectedModel: (selection: ModelSelection | null) => void;
  // Legacy integration-based selection (for backward compatibility)
  selectedIntegration: LLMIntegrationResponse | null;
  integrations: LLMIntegrationResponse[];
  loading: boolean;
  error: string | null;
  setSelectedIntegration: (integration: LLMIntegrationResponse | null) => void;
  refreshIntegrations: () => Promise<void>;
}

/**
 * Hook for managing LLM selection across different contexts in the app
 * Provides a consistent interface for LLM selection with context-specific state
 */
export const useLLMSelection = (options: UseLLMSelectionOptions = {}): UseLLMSelectionReturn => {
  const { context = 'global', autoLoad = true } = options;
  
  // Get the appropriate context-specific hook
  const toolsLLM = useToolsLLM();
  const agentLLM = useAgentLLM();
  const globalLLM = useGlobalLLM();
  const baseLLM = useLLM();

  // Select the appropriate context
  const contextData = (() => {
    switch (context) {
      case 'tools':
        return {
          selectedModel: toolsLLM.selectedModel,
          setSelectedModel: toolsLLM.setSelectedModel,
          selectedIntegration: toolsLLM.selectedIntegration,
          setSelectedIntegration: toolsLLM.setSelectedIntegration,
          integrations: toolsLLM.availableIntegrations,
          loading: toolsLLM.loading,
        };
      case 'agents':
        return {
          selectedModel: agentLLM.selectedModel,
          setSelectedModel: agentLLM.setSelectedModel,
          selectedIntegration: agentLLM.selectedIntegration,
          setSelectedIntegration: agentLLM.setSelectedIntegration,
          integrations: agentLLM.availableIntegrations,
          loading: agentLLM.loading,
        };
      case 'global':
      default:
        return {
          selectedModel: globalLLM.selectedModel,
          setSelectedModel: globalLLM.setSelectedModel,
          selectedIntegration: globalLLM.selectedIntegration,
          setSelectedIntegration: () => {}, // Global integration is read-only
          integrations: globalLLM.availableIntegrations,
          loading: globalLLM.loading,
        };
    }
  })();

  // Load integrations on mount if autoLoad is enabled
  const ranRef = useRef(false);
  useEffect(() => {
    if (ranRef.current) return;
    if (!autoLoad) return;
    if (!contextData.loading && contextData.integrations.length === 0) {
      ranRef.current = true;
      baseLLM.loadIntegrations();
    }
  }, [autoLoad, contextData.loading, contextData.integrations.length]);

  return {
    selectedModel: contextData.selectedModel,
    setSelectedModel: contextData.setSelectedModel,
    selectedIntegration: contextData.selectedIntegration,
    integrations: contextData.integrations,
    loading: contextData.loading,
    error: baseLLM.error,
    setSelectedIntegration: contextData.setSelectedIntegration,
    refreshIntegrations: baseLLM.refreshIntegrations,
  };
};

/**
 * Hook specifically for tools context
 */
export const useToolsLLMSelection = () => {
  return useLLMSelection({ context: 'tools' });
};

/**
 * Hook specifically for agents context
 */
export const useAgentsLLMSelection = () => {
  return useLLMSelection({ context: 'agents' });
};

/**
 * Hook for global LLM management (read-only selection)
 */
export const useGlobalLLMSelection = () => {
  return useLLMSelection({ context: 'global' });
};
