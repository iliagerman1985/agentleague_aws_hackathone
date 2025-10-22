/**
 * Modal for starting matchmaking with agent selection.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, Play } from 'lucide-react';
import { toast } from 'sonner';
import { gameMatchingApi, type JoinMatchmakingRequest } from '@/services/gameMatchingApi';
import { MatchmakingQueue } from './MatchmakingQueue';
import { agentsService, GameEnvironment, type AgentResponse, type AgentVersionResponse } from '@/services/agentsService';
import { GameApiService, type GameConfigOptionsResponse } from '@/services/gameApi';
import { type ChessMatchmakingConfig, type ChessTimeControl, type GameType } from '@/types/game';

import { useAuth } from '@/contexts/AuthContext';
interface AgentWithVersion {
  agent: AgentResponse;
  activeVersion: AgentVersionResponse | null;
}

interface MatchmakingModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  gameType: string;
  gameTypeName: string;
  preSelectedAgentId?: string;
  autoStart?: boolean; // Auto-start matchmaking when modal opens with pre-selected agent
}

const SUPPORTED_GAME_TYPES: GameType[] = ["texas_holdem", "chess"];

const isSupportedGameType = (value: string): value is GameType =>
  SUPPORTED_GAME_TYPES.includes(value as GameType);

export const MatchmakingModal: React.FC<MatchmakingModalProps> = ({
  open,
  onOpenChange,
  gameType,
  gameTypeName,
  preSelectedAgentId,
  autoStart = false,
}) => {
  const { refreshUser } = useAuth();
  const [agentsWithVersions, setAgentsWithVersions] = useState<AgentWithVersion[]>([]);
  const [selectedAgentVersionId, setSelectedAgentVersionId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [inQueue, setInQueue] = useState(false);
  const [gameId, setGameId] = useState<string | null>(null);

  const [headerStatus, setHeaderStatus] = useState<{ currentPlayers: number; minPlayers: number; maxPlayers: number } | null>(
    null
  );
  const [configOptions, setConfigOptions] = useState<Record<string, GameConfigOptionsResponse> | null>(null);
  const [selectedTimeControl, setSelectedTimeControl] = useState<ChessTimeControl>("long");
  const supportedGameType = isSupportedGameType(gameType) ? gameType : null;
  const chessTimeControlOptions =
    configOptions?.[GameEnvironment.CHESS]?.availableOptions?.time_control?.options ?? [];

  // Memoize the status update callback to prevent useEffect re-runs in MatchmakingQueue
  const handleStatusUpdate = useCallback((s: { currentPlayers: number; minPlayers: number; maxPlayers?: number }) => {
    setHeaderStatus({
      currentPlayers: s.currentPlayers,
      minPlayers: s.minPlayers,
      maxPlayers: s.maxPlayers ?? s.minPlayers
    });
  }, []);

  // Filter agents for this game type
  const gameAgents = supportedGameType
    ? agentsWithVersions.filter(
        (agentWithVersion) =>
          agentWithVersion.agent.gameEnvironment === supportedGameType &&
          !agentWithVersion.agent.isArchived &&
          agentWithVersion.activeVersion
      )
    : [];

  // Load agents with their active versions when modal opens
  useEffect(() => {
    if (open) {
      loadAgentsWithVersions();
      // Don't check matchmaking status on open - let users create new games freely
    }
  }, [open, gameType]);

  // Load config options when modal opens (used for time control)
  useEffect(() => {
    if (open) {
      GameApiService.getConfigOptions()
        .then(setConfigOptions)
        .catch(() => { /* ignore */ });
    }
  }, [open]);

  useEffect(() => {
    if (supportedGameType !== GameEnvironment.CHESS) {
      return;
    }

    const defaults = configOptions?.[GameEnvironment.CHESS]?.defaultConfig as Partial<ChessMatchmakingConfig> | undefined;
    if (defaults?.timeControl && defaults.timeControl !== selectedTimeControl) {
      setSelectedTimeControl(defaults.timeControl);
    }
  }, [supportedGameType, configOptions, selectedTimeControl]);

  const loadAgentsWithVersions = async () => {
    if (!supportedGameType) {
      setAgentsWithVersions([]);
      return;
    }

    try {
      const loadedAgents = await agentsService.list(supportedGameType as GameEnvironment);

      // Fetch active versions for each agent
      const agentsWithVersionsData: AgentWithVersion[] = await Promise.all(
        loadedAgents.map(async (agent) => {
          try {
            const activeVersion = await agentsService.getActiveVersion(agent.id);
            return { agent, activeVersion };
          } catch (error) {
            console.warn(`Failed to load active version for agent ${agent.id}:`, error);
            return { agent, activeVersion: null };
          }
        })
      );

      setAgentsWithVersions(agentsWithVersionsData);
    } catch (error) {
      console.error('Failed to load agents:', error);
      toast.error('Failed to load agents');
    }
  };



  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setInQueue(false);
      setGameId(null);
      setSelectedAgentVersionId('');
    }
  }, [open]);

  // Auto-select agent based on preSelectedAgentId or if only one available
  useEffect(() => {
    const availableAgents = gameAgents.filter(av => av.activeVersion);

    // If a specific agent was pre-selected, use it
    if (preSelectedAgentId && !selectedAgentVersionId) {
      const preSelectedAgent = availableAgents.find(av => av.agent.id === preSelectedAgentId);
      if (preSelectedAgent?.activeVersion) {
        setSelectedAgentVersionId(String(preSelectedAgent.activeVersion.id));
        return;
      }
    }

    // Otherwise, auto-select first agent if only one available
    if (availableAgents.length === 1 && !selectedAgentVersionId) {
      setSelectedAgentVersionId(String(availableAgents[0].activeVersion!.id));
    }
  }, [gameAgents, selectedAgentVersionId, preSelectedAgentId]);

  // Auto-start matchmaking when autoStart is enabled and agent is selected
  useEffect(() => {
    if (autoStart && selectedAgentVersionId && open && !inQueue && !loading) {
      handleStartMatchmaking();
    }
  }, [autoStart, selectedAgentVersionId, open, inQueue, loading]);


  const handleStartMatchmaking = async () => {
    if (!selectedAgentVersionId) {
      toast.error('Please select an agent');
      return;
    }

    setLoading(true);
    try {
      if (!supportedGameType) {
        toast.error('Unsupported game type');
        return;
      }

      let payload: JoinMatchmakingRequest = {
        gameType: supportedGameType,
        agentVersionId: selectedAgentVersionId,
      };

      if (supportedGameType === GameEnvironment.CHESS) {
        const chessDefaults = (configOptions?.[GameEnvironment.CHESS]?.defaultConfig ?? {}) as Partial<ChessMatchmakingConfig>;
        const chessConfig: ChessMatchmakingConfig = {
          env: GameEnvironment.CHESS,
          minPlayers: chessDefaults.minPlayers ?? 2,
          maxPlayers: chessDefaults.maxPlayers ?? 2,
          timeControl: selectedTimeControl,
          ...(chessDefaults.disableTimers !== undefined ? { disableTimers: chessDefaults.disableTimers } : {}),
        };

        payload = { ...payload, config: chessConfig };
      }

      const response = await gameMatchingApi.joinMatchmaking(payload);

      setGameId(response.gameId);
      await refreshUser();

      // Initialize header status from join response
      setHeaderStatus({
        currentPlayers: response.currentPlayers,
        minPlayers: response.minPlayers,
        maxPlayers: response.maxPlayers ?? response.minPlayers,
      });

      // Check if agent was already in a game
      if (response.matchmakingStatus === 'in_progress') {
        // Agent is already in an active game
        toast.info('Your agent is already in an active game', {
          duration: 4000,
        });
        setInQueue(true);
      } else if (response.matchmakingStatus === 'waiting') {
        // Agent joined or was already in waiting queue
        setInQueue(true);
        toast.success('Joined matchmaking queue!');
      } else {
        // New game created
        setInQueue(true);
        toast.success('Joined matchmaking queue!');
      }
    } catch (error: any) {
      console.error('Error joining matchmaking:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to join matchmaking';
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleGameStarted = (_startedGameId: string) => {
    toast.success('Game started!');
    onOpenChange(false);
  };

  const handleCancelled = () => {
    setInQueue(false);
    setGameId(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={inQueue ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-[500px] rounded-lg" onInteractOutside={(e) => inQueue && e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Play - {gameTypeName}</DialogTitle>
          <DialogDescription>
            {inQueue
              ? (headerStatus
                  ? `Waiting… ${headerStatus.currentPlayers}/${headerStatus.minPlayers} to start`
                  : 'Waiting for players to join...')
              : 'Select an agent to join the matchmaking queue'}
          </DialogDescription>
          {inQueue && headerStatus && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Players joined:</span>
                <span className="font-semibold">
                  {headerStatus.currentPlayers} / {headerStatus.maxPlayers}
                </span>
              </div>
              <Progress
                value={(headerStatus.currentPlayers / headerStatus.maxPlayers) * 100}
                className="h-2"
              />
              {headerStatus.currentPlayers < headerStatus.minPlayers && (
                <p className="text-xs text-muted-foreground text-center">
                  Need {headerStatus.minPlayers - headerStatus.currentPlayers} more to start
                </p>
              )}
            </div>
          )}
        </DialogHeader>

        {inQueue && gameId ? (
          <MatchmakingQueue
            gameId={gameId}
            gameType={gameType}
            onGameStarted={handleGameStarted}
            onCancelled={handleCancelled}
            onStatusUpdate={handleStatusUpdate}
          />
        ) : (
          <div className="space-y-6 py-4">
            {/* Agent selection */}
            <div className="space-y-2">
              <Label htmlFor="agent-select">Select Agent</Label>
              {gameAgents.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No agents available for {gameTypeName}. Create an agent first.
                </p>
              ) : (
                <Select value={selectedAgentVersionId} onValueChange={setSelectedAgentVersionId}>

                  <SelectTrigger id="agent-select" className="rounded-md">
                    <SelectValue placeholder="Choose an agent" />
                  </SelectTrigger>
                  <SelectContent>
                    {gameAgents.map((agentWithVersion) => (
                      <SelectItem key={agentWithVersion.agent.id} value={String(agentWithVersion.activeVersion!.id)}>
                        {agentWithVersion.agent.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Chess time control selection */}
            {supportedGameType === GameEnvironment.CHESS &&
              configOptions?.[GameEnvironment.CHESS]?.availableOptions?.time_control && (
              <div className="space-y-2">
                <Label htmlFor="time-control">Time control</Label>
                <Select
                  value={selectedTimeControl}
                  onValueChange={(value) => setSelectedTimeControl(value as ChessTimeControl)}
                >
                  <SelectTrigger id="time-control" className="rounded-md">
                    <SelectValue placeholder="Choose time control" />
                  </SelectTrigger>
                  <SelectContent>
                    {chessTimeControlOptions.map((opt) => (
                      <SelectItem key={String(opt.value)} value={String(opt.value)}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Info text */}
            <div className="rounded-lg bg-muted p-4 text-sm text-muted-foreground">
              <p>
                You'll be matched with other players or system agents. The game will start
                automatically when enough players join or after the waiting period.
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1 rounded-md"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>

              <Button
                className="flex-1 rounded-md bg-brand-teal hover:bg-brand-teal/90"
                onClick={handleStartMatchmaking}
                disabled={loading || !selectedAgentVersionId || gameAgents.length === 0}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Joining...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Play
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

