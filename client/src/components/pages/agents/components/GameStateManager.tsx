import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Save,
  FolderOpen,
  Sparkles,
  ChevronDown,
  Clock
} from 'lucide-react';
import { type AgentId } from '@/types/ids';
import { api } from '@/lib/api';
import { type TestScenarioResponse, GameEnvironment } from '@/services/agentsService';
import { SaveGameStateDialog } from '../dialogs/SaveGameStateDialog';
import { SavedStatesDialog } from '../dialogs/SavedStatesDialog';
import { StateChatDialog } from '../dialogs/StateChatDialog';
import { ConfirmDialog } from '@/components/common';

interface GameStateManagerProps {
  agentId: AgentId;
  gameState: Record<string, any>;
  onLoadState: (gameState: Record<string, any>, description?: string) => void;
  iterationCount: number;
  maxIterations: number;
  running?: boolean;
  showGenerateButton?: boolean;
  showGameConfigHeader?: boolean;
  environment?: GameEnvironment;
}

export const GameStateManager: React.FC<GameStateManagerProps> = ({
  agentId,
  gameState,
  onLoadState,
  iterationCount,
  showGenerateButton = false, // Changed default to false - generation removed from Agent Test tab
  environment,
}) => {
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [confirmLoadOpen, setConfirmLoadOpen] = useState(false);
  const [pendingLoadState, setPendingLoadState] = useState<{
    gameState: Record<string, any>;
    description?: string;
  } | null>(null);
  const [recentStates, setRecentStates] = useState<TestScenarioResponse[]>([]);
  const [currentDescription, setCurrentDescription] = useState<string | undefined>(undefined);

  // Load recent states when component mounts
  useEffect(() => {
    loadRecentStates();
  }, [agentId]);

  const loadRecentStates = async () => {
    try {
      const states = await api.agents.getSavedGameStates(agentId, { limit: 5 });
      setRecentStates(states);
    } catch (err) {
      console.error('Failed to load recent states:', err);
    }
  };

  const handleSaveSuccess = () => {
    // Refresh recent states
    loadRecentStates();
  };

  const handleLoadStateRequest = (gameState: Record<string, any>, description?: string) => {
    // If there are iterations in progress, show confirmation
    if (iterationCount > 0) {
      setPendingLoadState({ gameState, description });
      setConfirmLoadOpen(true);
    } else {
      onLoadState(gameState, description);
      setCurrentDescription(description);
    }
  };

  const handleConfirmLoad = () => {
    if (pendingLoadState) {
      onLoadState(pendingLoadState.gameState, pendingLoadState.description);
      setCurrentDescription(pendingLoadState.description);
      setPendingLoadState(null);
    }
    setConfirmLoadOpen(false);
  };

  const handleQuickLoad = (state: TestScenarioResponse) => {
    handleLoadStateRequest(state.gameState, state.description || undefined);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isGameStateEmpty = () => {
    return !gameState || Object.keys(gameState).length === 0 ||
           (gameState.state && Object.keys(gameState.state).length === 0);
  };

  return (
    <>
      {/* Button layout - centered */}
      <div className="flex items-center justify-center gap-2 flex-wrap">
        {/* Save Button - More visible */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSaveDialogOpen(true)}
          disabled={isGameStateEmpty()}
          className="flex items-center gap-1.5 bg-brand-orange/10 hover:bg-brand-orange/20 text-brand-orange border-brand-orange/30 transition-all duration-200 shadow-sm font-medium"
        >
          <Save className="h-4 w-4" />
          <span>Save</span>
        </Button>

        {/* Load Dropdown - More visible */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="flex items-center gap-1.5 bg-brand-blue/10 hover:bg-brand-blue/20 text-brand-blue border-brand-blue/30 transition-all duration-200 shadow-sm font-medium">
              <FolderOpen className="h-4 w-4" />
              <span>Load</span>
              <ChevronDown className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel>Quick Load</DropdownMenuLabel>
            {recentStates.length > 0 ? (
              <>
                {recentStates.map((state) => (
                  <DropdownMenuItem
                    key={state.id}
                    onClick={() => handleQuickLoad(state)}
                    className="flex flex-col items-start gap-1 py-2"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-medium truncate">{state.name}</span>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {formatDate(state.createdAt)}
                      </div>
                    </div>
                    {state.description && (
                      <span className="text-xs text-muted-foreground line-clamp-1">
                        {state.description}
                      </span>
                    )}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
              </>
            ) : (
              <DropdownMenuItem disabled>
                <span className="text-muted-foreground">No saved states</span>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => setLoadDialogOpen(true)}>
              <FolderOpen className="h-4 w-4 mr-2" />
              Browse All States...
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Generate Button - conditionally shown */}
        {showGenerateButton && (
          <Button
            variant="brand-accent"
            size="sm"
            onClick={() => setGenerateDialogOpen(true)}
            className="flex items-center gap-1"
          >
            <Sparkles className="h-4 w-4" />
            <span className="hidden sm:inline">{isGameStateEmpty() ? 'Generate' : 'Edit'}</span>
          </Button>
        )}
      </div>

      {/* Save Game State Dialog */}
      <SaveGameStateDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        agentId={agentId}
        gameState={gameState}
        initialDescription={currentDescription}
        onSaved={handleSaveSuccess}
      />

      {/* Load Saved States Dialog */}
      <SavedStatesDialog
        open={loadDialogOpen}
        onOpenChange={setLoadDialogOpen}
        environment={environment}
        onLoadState={handleLoadStateRequest}
      />

      {/* State Chat Dialog (Generate/Edit) */}
      <StateChatDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        agentId={agentId}
        initialState={gameState}
        initialDescription={undefined}
        onApply={(stateObj, desc) => {
          handleLoadStateRequest(stateObj, desc);
        }}
      />

      {/* Confirm Load Dialog */}
      <ConfirmDialog
        open={confirmLoadOpen}
        onOpenChange={setConfirmLoadOpen}
        title="Load Game State"
        description="Loading a new game state will reset the current test session. Are you sure you want to continue?"
        onConfirm={handleConfirmLoad}
      />
    </>
  );
};
