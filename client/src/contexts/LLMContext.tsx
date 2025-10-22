import React, { createContext, useContext, useState, useEffect, useRef, useMemo, useCallback, ReactNode } from "react";
import { api, LLMIntegrationResponse, ModelSelection } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

interface LLMContextType {
  // Current integrations
  integrations: LLMIntegrationResponse[];
  loading: boolean;
  error: string | null;

  // Global default integration (legacy)
  defaultIntegration: LLMIntegrationResponse | null;

  // Context-specific model selections
  toolsModelSelection: ModelSelection | null;
  agentModelSelection: ModelSelection | null;
  globalModelSelection: ModelSelection | null;

  // Legacy integration selections (for backward compatibility)
  toolsIntegration: LLMIntegrationResponse | null;
  agentIntegration: LLMIntegrationResponse | null;

  // Actions
  loadIntegrations: () => Promise<void>;
  setToolsModelSelection: (selection: ModelSelection | null) => void;
  setAgentModelSelection: (selection: ModelSelection | null) => void;
  setGlobalModelSelection: (selection: ModelSelection | null) => void;
  setToolsIntegration: (integration: LLMIntegrationResponse | null) => void;
  setAgentIntegration: (integration: LLMIntegrationResponse | null) => void;
  refreshIntegrations: () => Promise<void>;
}

const LLMContext = createContext<LLMContextType | undefined>(undefined);

interface LLMProviderProps {
  children: ReactNode;
}

export const LLMProvider: React.FC<LLMProviderProps> = ({ children }) => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [integrations, setIntegrations] = useState<LLMIntegrationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [defaultIntegration, setDefaultIntegration] = useState<LLMIntegrationResponse | null>(null);

  // Model-based selections with localStorage persistence
  const [toolsModelSelection, setToolsModelSelectionState] = useState<ModelSelection | null>(() => {
    const saved = localStorage.getItem('llm-tools-model-selection');
    return saved ? JSON.parse(saved) : null;
  });

  const [agentModelSelection, setAgentModelSelectionState] = useState<ModelSelection | null>(() => {
    try {
      const saved = localStorage.getItem('llm-agent-model-selection');
      return saved ? JSON.parse(saved) : null;
    } catch (error) {
      console.error('LLMContext: Error loading agent model from localStorage', error);
      return null;
    }
  });

  const [globalModelSelection, setGlobalModelSelectionState] = useState<ModelSelection | null>(() => {
    const saved = localStorage.getItem('llm-global-model-selection');
    return saved ? JSON.parse(saved) : null;
  });

  // Legacy integration selections (for backward compatibility)
  const [toolsIntegration, setToolsIntegration] = useState<LLMIntegrationResponse | null>(null);
  const [agentIntegration, setAgentIntegration] = useState<LLMIntegrationResponse | null>(null);

  // Model selection setters with localStorage persistence
  const setToolsModelSelection = (selection: ModelSelection | null) => {
    setToolsModelSelectionState(selection);
    if (selection) {
      localStorage.setItem('llm-tools-model-selection', JSON.stringify(selection));
    } else {
      localStorage.removeItem('llm-tools-model-selection');
    }
  };

  const setAgentModelSelection = (selection: ModelSelection | null) => {
    setAgentModelSelectionState(selection);
    if (selection) {
      localStorage.setItem('llm-agent-model-selection', JSON.stringify(selection));
    } else {
      localStorage.removeItem('llm-agent-model-selection');
    }
  };

  const setGlobalModelSelection = (selection: ModelSelection | null) => {
    setGlobalModelSelectionState(selection);
    if (selection) {
      localStorage.setItem('llm-global-model-selection', JSON.stringify(selection));
    } else {
      localStorage.removeItem('llm-global-model-selection');
    }
  };

  const loadIntegrations = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.llmIntegrations.list();
      setIntegrations(data);
      
      // Find default integration
      const defaultInt = data.find(i => i.isDefault) || null;
      setDefaultIntegration(defaultInt);
      
      // Initialize context-specific integrations if not set
      if (!toolsIntegration && defaultInt) {
        setToolsIntegration(defaultInt);
      }
      if (!agentIntegration && defaultInt) {
        setAgentIntegration(defaultInt);
      }
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load integrations";

      // Check if this is an authentication error
      if (errorMessage.includes('Authentication required') || errorMessage.includes('401') || errorMessage.includes('403')) {
        // Don't set error state for auth errors, let the automatic re-login handle it
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [agentIntegration, toolsIntegration]);

  const refreshIntegrations = useCallback(async () => {
    await loadIntegrations();
    // Clear selections that point to deleted integrations
    setToolsModelSelectionState(prev => (prev && !integrations.find(i => i.id === prev.integrationId) ? null : prev));
    setAgentModelSelectionState(prev => (prev && !integrations.find(i => i.id === prev.integrationId) ? null : prev));
    setGlobalModelSelectionState(prev => (prev && !integrations.find(i => i.id === prev.integrationId) ? null : prev));
    setToolsIntegration(prev => (prev && !integrations.find(i => i.id === prev.id) ? null : prev));
    setAgentIntegration(prev => (prev && !integrations.find(i => i.id === prev.id) ? null : prev));
  }, [loadIntegrations, integrations]);

  // Load integrations when authenticated (guard for StrictMode double-invoke)
  const didInit = useRef(false);
  useEffect(() => {
    if (didInit.current || authLoading || !isAuthenticated) return;
    didInit.current = true;
    loadIntegrations();
  }, [loadIntegrations, isAuthenticated, authLoading]);

  // Reset initialization flag when auth state changes
  useEffect(() => {
    if (!isAuthenticated) {
      didInit.current = false;
      setIntegrations([]);
      setDefaultIntegration(null);
      setError(null);
    }
  }, [isAuthenticated]);

  // Update context-specific integrations when default changes
  useEffect(() => {
    if (defaultIntegration) {
      // Only update if current selection is null or no longer exists in integrations
      if (!toolsIntegration || !integrations.find(i => i.id === toolsIntegration.id)) {
        setToolsIntegration(defaultIntegration);
      }
      if (!agentIntegration || !integrations.find(i => i.id === agentIntegration.id)) {
        setAgentIntegration(defaultIntegration);
      }
    }
  }, [defaultIntegration, integrations, toolsIntegration, agentIntegration]);

  const value: LLMContextType = useMemo(() => ({
    integrations,
    loading,
    error,
    defaultIntegration,
    toolsModelSelection,
    agentModelSelection,
    globalModelSelection,
    toolsIntegration,
    agentIntegration,
    loadIntegrations,
    setToolsModelSelection,
    setAgentModelSelection,
    setGlobalModelSelection,
    setToolsIntegration,
    setAgentIntegration,
    refreshIntegrations,
  }), [
    integrations, loading, error, defaultIntegration,
    toolsModelSelection, agentModelSelection, globalModelSelection,
    toolsIntegration, agentIntegration,
    loadIntegrations, refreshIntegrations,
  ]);

  return (
    <LLMContext.Provider value={value}>
      {children}
    </LLMContext.Provider>
  );
};

export const useLLM = (): LLMContextType => {
  const context = useContext(LLMContext);
  if (context === undefined) {
    throw new Error("useLLM must be used within an LLMProvider");
  }
  return context;
};

// Hook for tools-specific LLM model selection
export const useToolsLLM = () => {
  const {
    toolsModelSelection,
    setToolsModelSelection,
    toolsIntegration,
    setToolsIntegration,
    integrations,
    loading
  } = useLLM();

  return {
    // New model-based selection
    selectedModel: toolsModelSelection,
    setSelectedModel: setToolsModelSelection,
    // Legacy integration-based selection (for backward compatibility)
    selectedIntegration: toolsIntegration,
    setSelectedIntegration: setToolsIntegration,
    availableIntegrations: integrations,
    loading,
  };
};

// Hook for agent-specific LLM model selection
export const useAgentLLM = () => {
  const {
    agentModelSelection,
    setAgentModelSelection,
    agentIntegration,
    setAgentIntegration,
    integrations,
    loading
  } = useLLM();

  return {
    // New model-based selection
    selectedModel: agentModelSelection,
    setSelectedModel: setAgentModelSelection,
    // Legacy integration-based selection (for backward compatibility)
    selectedIntegration: agentIntegration,
    setSelectedIntegration: setAgentIntegration,
    availableIntegrations: integrations,
    loading,
  };
};

// Hook for global LLM model selection
export const useGlobalLLM = () => {
  const {
    globalModelSelection,
    setGlobalModelSelection,
    defaultIntegration,
    integrations,
    loading
  } = useLLM();

  return {
    // New model-based selection
    selectedModel: globalModelSelection,
    setSelectedModel: setGlobalModelSelection,
    // Legacy integration-based selection (for backward compatibility)
    selectedIntegration: defaultIntegration,
    availableIntegrations: integrations,
    loading,
  };
};

export default LLMContext;
