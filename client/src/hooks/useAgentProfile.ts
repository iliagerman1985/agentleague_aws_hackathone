import { useState } from 'react';
import { type AgentId } from '@/types/ids';

/**
 * Hook to manage agent profile modal state
 * Use this throughout the app to show agent profiles when clicking on agents
 */
export const useAgentProfile = () => {
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId | null>(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const showAgentProfile = (agentId: AgentId) => {
    setSelectedAgentId(agentId);
    setIsProfileOpen(true);
  };

  const closeAgentProfile = () => {
    setIsProfileOpen(false);
    // Keep the agent ID until the modal is fully closed for smooth transitions
    setTimeout(() => setSelectedAgentId(null), 300);
  };

  return {
    selectedAgentId,
    isProfileOpen,
    showAgentProfile,
    closeAgentProfile,
  };
};

