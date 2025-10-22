import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useToasts } from '@/components/common/notifications/ToastProvider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, ArrowLeft, RefreshCw } from 'lucide-react';
// PageContainer import removed - not used in this component
import {
  PokerTable
} from '@/components/poker';
import { GameEvent, EventLog } from '@/components/games/EventLog';
import { SharedModal } from '@/components/common/SharedModal';
import {
  PokerApiService,
  GameStateResponse,
  PlayerInfo,
  TexasHoldemAction,
  TexasHoldemMove,
  PlayerStatus,
  PokerUtils,
  TexasHoldemState
} from '@/services/pokerApi';
import { type GameId, type AgentVersionId, type PlayerId } from '@/types/ids';
import { useAuth } from '@/contexts/AuthContext';
import { GameVictoryModal } from '@/components/games/GameVictoryModal';

import { useStateHistory } from '@/hooks/useStateHistory';
// TEMPORARY: Show agent play button in real games (not just playground)
// Set to false to hide the button, or comment out the entire line to remove the feature
const SHOW_AGENT_PLAY_IN_REAL_GAMES = true;

// Helper functions to cast strings to branded types
const toGameId = (id: string): GameId => id as unknown as GameId;
const toAgentVersionId = (id: string): AgentVersionId => id as unknown as AgentVersionId;
const toPlayerId = (id: string): PlayerId => id as unknown as PlayerId;

interface PokerGameProps {
  // Optional props for testing or direct game creation
  initialGameId?: string;
  /** If true, this game is embedded in another page (e.g., Agent Run tab) */
  isEmbedded?: boolean;
  /** Callback when reset is requested (only used when isEmbedded=true) */
  onReset?: () => void;
}

export const PokerGame: React.FC<PokerGameProps> = ({ initialGameId, isEmbedded = false, onReset }) => {
  const { gameId: routeGameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const { push } = useToasts();
  const { updateCoinsBalance } = useAuth();

  // Use initialGameId prop or route param
  const gameId = initialGameId || routeGameId;

  // Game state
  const [gameState, setGameState] = useState<GameStateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Players information
  const [players, setPlayers] = useState<PlayerInfo[]>([]);

  // User's existing games
  const [userGames, setUserGames] = useState<GameStateResponse[]>([]);
  const [loadingGames, setLoadingGames] = useState(false);

  // Use ref to track current gameId
  const gameIdRef = useRef<string | undefined>(gameId);

  // Update gameIdRef when gameId changes
  useEffect(() => {
    gameIdRef.current = gameId;
  }, [gameId]);
  // Client-side state history for undo/redo and branching
  const { current: histState, reset, push: pushHist, canUndo, canRedo, undo, redo } = useStateHistory<TexasHoldemState>();
  const lastPushedRef = useRef<{ id: string | undefined; v: number } | null>(null);

  useEffect(() => {
    if (!gameState) return;
    const id = gameState.id as unknown as string | undefined;
    const v = (gameState.version ?? 0) as number;
    if (!lastPushedRef.current || lastPushedRef.current.id !== id) {
      reset(gameState.state as TexasHoldemState);
      lastPushedRef.current = { id, v };
      return;
    }
    if (lastPushedRef.current.v !== v) {
      pushHist(gameState.state as TexasHoldemState);
      lastPushedRef.current.v = v;
    }
  }, [gameState?.id, gameState?.version]);

  const renderState: TexasHoldemState | undefined = (histState ?? gameState?.state) as TexasHoldemState | undefined;
  const atLatest = !canRedo;

  const ensureBranchIfNeeded = useCallback(async (): Promise<{ gameId: GameId; state: TexasHoldemState } | null> => {
    if (!gameId && !gameState) return null;
    if (atLatest && gameId && gameState) {
      return { gameId: toGameId(gameId), state: gameState.state as TexasHoldemState };
    }
    const s = (renderState ?? (gameState?.state as TexasHoldemState)) as TexasHoldemState;
    const agentVersionId = gameState?.players?.[0]?.agentVersionId;

    const created = await PokerApiService.createPlaygroundFromState({
      agentId: toAgentVersionId(String(agentVersionId)),
      stateView: s as any,
      config: {},
      numPlayers: s.players?.length ?? undefined,
    });
    setGameState(created);
    reset(created.state as TexasHoldemState);
    navigate(`/games/texas-holdem/${created.id}`);
    return { gameId: created.id, state: created.state as TexasHoldemState };
  }, [atLatest, gameId, gameState, renderState]);

  // UI state
  const [processingAction, setProcessingAction] = useState(false);
  // Event log modal state
  const [eventLogModalOpen, setEventLogModalOpen] = useState(false);
  // Victory modal state
  const [victoryModalOpen, setVictoryModalOpen] = useState<boolean>(false);
  const [isVictory, setIsVictory] = useState<boolean>(false);
  const [hasShownVictoryModal, setHasShownVictoryModal] = useState<boolean>(false);

  // Current player state (for demo purposes, we'll assume we're controlling the current player)
  const currentPlayerId = gameState?.state.currentPlayerId;
  const actionPosition = gameState?.state.actionPosition;
  const currentPlayer = gameState?.state.players.find((_, index) => index === actionPosition);
  const isPlayerTurn = Boolean(typeof actionPosition === 'number' && actionPosition >= 0 && currentPlayer);

  // Helper to get player name by PlayerId
  const getPlayerNameById = useCallback((playerId: string) => {
    if (!gameState) return 'Unknown Player';
    const player = players.find(p => p.id === playerId);
    return player?.name || `Player ${playerId.slice(-8)}`;
  }, [gameState, players]);

  // Helper function to add events to the log
  const addEvent = useCallback((type: GameEvent['type'], message: string, playerId?: string, playerName?: string, details?: any) => {
    // Events are now handled directly by EventLog component from gameState.events
    // This function is kept for system events like loading, errors, etc.
    console.log(`Event: [${type}] ${message}`, { playerId, playerName, details });
  }, []);

  // Load game state
  const loadGameState = useCallback(async () => {
    const currentGameId = gameIdRef.current;
    if (!currentGameId) return;

    setLoading(true);
    setError(null);

    // Add system event for loading
    addEvent('system', `Loading game state for game ${currentGameId.slice(-8)}...`);

    try {
      const state = await PokerApiService.getGameState(toGameId(currentGameId));
      setGameState(state);

      // Use players from the game state response
      if (state.players) {
        setPlayers(state.players);
        addEvent('system', `Loaded ${state.players.length} players`);
      } else {
        addEvent('system', 'No players available in game state');
      }

      // Add success event
      addEvent('system', 'Game state loaded successfully');

      // Events are now handled by the EventLog component directly from state.events
      // No need to duplicate them in gameEvents
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load game state';
      setError(errorMessage);
      push({ message: errorMessage, tone: 'error' });
      addEvent('error', `Failed to load game state: ${errorMessage}`, undefined, undefined, err);
    } finally {
      setLoading(false);
    }
  }, [addEvent, push]);

  // Load user's existing games
  const loadUserGames = useCallback(async () => {
    setLoadingGames(true);
    try {
      const games = await PokerApiService.getUserGames('texas_holdem', false);
      setUserGames(games);
    } catch (err) {
      console.error('Failed to load user games:', err);
      // Don't show error toast for this, just log it
    } finally {
      setLoadingGames(false);
    }
  }, []);

  // Handle observing an existing game
  const handleObserveGame = (game: GameStateResponse) => {
    navigate(`/games/texas-holdem/${game.id}`);
  };

  // Stop polling - kept for cleanup in useEffect
  const stopPolling = useCallback(() => {
    // No-op now, but kept for compatibility with existing cleanup code
  }, []);

  // Player actions - send move override to backend
  const handlePlayerAction = async (action: TexasHoldemAction, amount?: number) => {
    if (processingAction) return;

    // Get current player info for event logging (based on latest visible state)
    const activePlayer = (renderState?.players || []).find((_, index) => index === renderState?.actionPosition);
    const playerName = activePlayer?.playerId ? getPlayerNameById(activePlayer.playerId) : 'Unknown Player';
    const actionMsg = `Manual action: ${action}${amount ? ` $${amount}` : ''}`;

    addEvent('action', actionMsg, activePlayer?.playerId, playerName);

    setProcessingAction(true);
    try {
      const base = await ensureBranchIfNeeded();
      if (!base) throw new Error('No game loaded');
      const moveOverride: TexasHoldemMove = { action, amount: amount || undefined };
      const playerId = base.state.currentPlayerId;
      if (!playerId) throw new Error('No current player ID available');

      const turn = base.state.turn || 0;
      const result = await PokerApiService.executeTurn(base.gameId, toPlayerId(playerId), moveOverride, turn);
      push({ message: `Action: ${action}${amount ? ` $${amount}` : ''}`, tone: 'success' });

      addEvent('action', `Manual action completed: ${action}${amount ? ` $${amount}` : ''}`, activePlayer?.playerId, playerName);

      setGameState(prev => prev && prev.id === base.gameId ? {
        ...prev,
        state: result.newState,
        events: [...(prev.events || []), ...(Array.isArray(result.newEvents) ? result.newEvents : [])],
        version: result.version
      } : prev);

      // Update coins balance immediately from response
      if (result.newCoinsBalance !== undefined && result.newCoinsBalance !== null) {
        updateCoinsBalance(result.newCoinsBalance);
      }
    } catch (err) {
      console.error('Player action execution failed:', err);
      let errorMessage = 'Failed to perform action';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'object' && err !== null) {
        const errorObj = err as any;
        if (errorObj.message) errorMessage = errorObj.message;
        else if (errorObj.detail) errorMessage = errorObj.detail;
      }
      push({ message: errorMessage, tone: 'error' });
      const errorPlayer = (renderState?.players || []).find((_, index) => index === renderState?.actionPosition);
      const errorPlayerName = errorPlayer?.playerId ? getPlayerNameById(errorPlayer.playerId) : 'Unknown Player';
      addEvent('error', `Manual action failed: ${errorMessage}`, errorPlayer?.playerId, errorPlayerName, err);
    } finally {
      setProcessingAction(false);
    }
  };

  // Handle agent turn (no move override)
  const handleAgentTurn = async () => {
    // Base state and branching if needed
    const base = await ensureBranchIfNeeded();
    if (!base) {
      const errorMsg = 'Game not loaded';
      push({ message: errorMsg, tone: 'error' });
      addEvent('error', errorMsg);
      return;
    }

    const currentPlayerId = base.state.currentPlayerId;
    if (!currentPlayerId) {
      const errorMsg = 'No current player ID available';
      push({ message: errorMsg, tone: 'error' });
      addEvent('error', errorMsg);
      return;
    }

    const agentPlayer = base.state.players.find((_, index) => index === base.state.actionPosition);
    const playerName = agentPlayer?.playerId ? getPlayerNameById(agentPlayer.playerId) : 'Unknown Player';
    addEvent('action', 'Playing agent turn...', agentPlayer?.playerId, playerName);

    setProcessingAction(true);
    try {
      const turn = base.state.turn || 0;
      const result = await PokerApiService.executeTurn(base.gameId, toPlayerId(currentPlayerId), undefined, turn);
      push({ message: 'Agent turn executed', tone: 'success' });
      addEvent('action', 'Agent turn completed successfully', agentPlayer?.playerId, playerName);

      setGameState(prev => prev && prev.id === base.gameId ? {
        ...prev,
        state: result.newState,
        events: [...(prev.events || []), ...(Array.isArray(result.newEvents) ? result.newEvents : [])],
        version: result.version
      } : prev);

      // Update coins balance immediately from response
      if (result.newCoinsBalance !== undefined && result.newCoinsBalance !== null) {
        updateCoinsBalance(result.newCoinsBalance);
      }
    } catch (err) {
      console.error('Agent turn execution failed:', err);
      let errorMessage = 'Failed to execute agent turn';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'object' && err !== null) {
        const errorObj = err as any;
        if (errorObj.message) {
          errorMessage = errorObj.message;
        } else if (errorObj.detail) {
          errorMessage = errorObj.detail;
        }
      }
      push({ message: errorMessage, tone: 'error' });
      const errorAgentPlayer = base.state.players.find((_, index) => index === base.state.actionPosition);
      const errorPlayerName = errorAgentPlayer?.playerId ? getPlayerNameById(errorAgentPlayer.playerId) : 'Unknown Player';
      addEvent('error', errorMessage, errorAgentPlayer?.playerId, errorPlayerName, err);
    } finally {
      setProcessingAction(false);
    }
  };

  // Leave game
  const handleLeaveGame = () => {
    stopPolling();
    // Clear game state before navigating
    setGameState(null);
    setError(null);
    setProcessingAction(false);

    // Contextual navigation:
    // - If we have a gameId, we're inside a game, so go back to Texas Hold'em lobby
    // - If no gameId, we're in Texas Hold'em lobby, so go back to main games screen
    if (gameId) {
      navigate('/games/texas-holdem');
    } else {
      navigate('/games');
    }
  };

  // Effects - load game state when gameId changes
  useEffect(() => {
    if (gameId) {
      console.log('🎯 useEffect: Loading game state for gameId:', gameId);
      // Add welcome event
      addEvent('system', `Joined game ${gameId.slice(-8)}`);
      loadGameState(); // Load game state once
    } else {
      console.log('🎯 useEffect: No gameId, clearing state and loading user games');
      // Clear game state when no gameId (back to lobby)
      setGameState(null);
      setError(null);
      setProcessingAction(false);
      stopPolling();
      // Load user's existing games for the lobby
      loadUserGames();
    }
  }, [gameId, loadGameState, loadUserGames, addEvent]); // Depend on gameId and loadGameState

  // Long poll for game state updates during active gameplay
  useEffect(() => {
    if (!gameId || !gameState) return;

    // Don't poll if game is finished
    if (gameState.state?.isFinished) return;

    let isActive = true;
    let currentVersion = gameState.version ?? 0;

    const longPoll = async () => {
      while (isActive && !gameState.state?.isFinished) {
        try {
          // Long poll with current version - server will wait until version changes
          const updatedState = await PokerApiService.getGameState(
            toGameId(gameId),
            currentVersion,  // Use local version tracker
            30  // 30 second timeout
          );

          if (!isActive) return;

          // Update local version and state
          currentVersion = updatedState.version ?? 0;
          setGameState(updatedState);

          // Update players if they changed
          if (updatedState.players) {
            setPlayers(updatedState.players);
          }
        } catch (error) {
          // If 404, game doesn't exist - stop polling
          if (error instanceof Error && error.message.includes('404')) {
            console.log('[PokerGame] Game not found (404), stopping polling');
            isActive = false;
            push({ message: 'Game no longer exists', tone: 'error' });
            break;
          }
          // For other errors, wait a bit before retrying
          if (isActive) {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        }
      }
    };

    void longPoll();

    return () => {
      isActive = false;
    };
  }, [gameId, gameState?.version, gameState?.state?.isFinished, push]);

  // Victory modal detection - show modal when game finishes
  useEffect(() => {
    if (!gameState?.state?.isFinished || hasShownVictoryModal || isEmbedded) return;

    const state = gameState.state as TexasHoldemState;

    // Skip if no winners declared
    if (!state.winners || state.winners.length === 0) {
      return;
    }

    // Find the user's player in the game - look for the player with the highest chips
    // In poker, the user is typically the player with the most chips at the end
    const userPlayer = gameState.players?.[0]; // Assume first player is the user

    // Determine if user won - check if user's player ID is in the winners list
    const didUserWin = userPlayer && state.winners.some((winnerId: any) => String(winnerId) === String(userPlayer.id));

    setIsVictory(!!didUserWin);
    setVictoryModalOpen(true);
    setHasShownVictoryModal(true);
  }, [gameState?.state?.isFinished, gameState?.state?.winners, hasShownVictoryModal, isEmbedded, gameState?.players]);

  // Cleanup when component unmounts
  useEffect(() => {
    return () => {
      console.log('🎯 useEffect cleanup: Component unmounting');
    };
  }, []); // No dependencies - only run on mount/unmount

  // Convert game state to component props
  const getPlayersForTable = () => {
    if (!gameState) return [];

    const mappedPlayers = gameState.state.players.map((player, index) => {
      const isActive = index === actionPosition;

      // Get player info from stored players
      const playerInfo = players.find(p => p.id === player.playerId);
      const agentName = playerInfo?.name || `Player ${player.playerId?.slice(-8) || 'Unknown'}`;

      return {
        id: player.playerId,
        name: agentName,
        chipCount: player.chips,
        cards: player.holeCards || [],
        isActive: isActive,
        isFolded: player.status === PlayerStatus.FOLDED,
        isAllIn: player.status === PlayerStatus.ALL_IN,
        currentBet: player.currentBet,
        isDealer: index === gameState.state.dealerPosition,
        isSmallBlind: index === gameState.state.smallBlindPosition,
        isBigBlind: index === gameState.state.bigBlindPosition,
        position: index + 1, // Add explicit position (1-based for CSS classes)
      };
    });

    return mappedPlayers;
  };

  // Render loading state
  if (loading && !gameState) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p>Loading game...</p>
        </div>
      </div>
    );
  }

  // Handle error screen back button
  const handleErrorBack = () => {
    // Clear all error and loading states
    setError(null);
    setLoading(false);
    setProcessingAction(false);
    setGameState(null);
    stopPolling();
    // Navigate back to Texas Hold'em lobby
    navigate('/games/texas-holdem');
  };

  // Render error state
  if (error && !gameState) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Error</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p>{error}</p>
            <div className="flex space-x-2">
              <Button onClick={handleErrorBack} variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Lobby
              </Button>
              <Button onClick={() => loadGameState()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full h-full max-h-full flex flex-col">
      {/* Container card that holds header and content */}
      <div className="bg-card border border-border shadow-sm flex-1 w-full flex flex-col rounded-xl h-full max-h-full">
        {/* Header section */}

        <div className="bg-slate-800 text-white border-b border-border px-6 py-6 rounded-t-xl flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                onClick={handleLeaveGame}
                variant="outline"
                size="sm"
                className="bg-white/10 border-white/20 text-white hover:bg-white/20"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>

              <div>
                <h1 className="text-xl font-bold text-white">
                  {gameId ? `Texas Hold'em - Game ${gameId}` : 'Texas Hold\'em Poker'}
                </h1>
                <p className="text-white/70">
                  {gameId ? 'Live poker game in progress' : 'Create or join a poker game'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {gameState && (
                <>
                  <Badge variant="secondary" className="bg-white/10 text-white border-white/20">
                    {PokerUtils.getBettingRoundName(gameState.state.bettingRound)}
                  </Badge>

                  <Badge variant="default" className="bg-green-600">
                    Active
                  </Badge>

                  {gameState.state.isFinished && (
                    <Badge variant="destructive">
                      Finished
                    </Badge>
                  )}
                </>
              )}

              {gameId && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canUndo}
                    onClick={undo}
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                  >
                    Undo
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canRedo}
                    onClick={redo}
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                  >
                    Redo
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // If embedded and onReset callback provided, use it
                      if (isEmbedded && onReset) {
                        onReset();
                      }
                    }}
                    disabled={!isEmbedded || !onReset}
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                  >
                    Reset
                  </Button>
                  <Button
                    onClick={() => loadGameState()}
                    variant="outline"
                    size="sm"
                    disabled={loading}
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                  >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Content section */}
        <div className="flex-1 min-h-0 h-full">
          {/* Main Game Area with new design background */}
          <div className="h-full max-h-full" style={{ backgroundColor: 'var(--poker-bg-dark)' }}>
            {gameState ? (
              <div className="h-full max-h-full p-4">
                <PokerTable
                  players={getPlayersForTable()}
                  communityCards={renderState?.communityCards || []}
                  pot={renderState?.pot ?? 0}
                  currentPlayerId={(renderState?.currentPlayerId || currentPlayerId) || undefined}
                  isPlayerTurn={isPlayerTurn}
                  processingAction={processingAction}
                  events={gameState.events || []}
                  isPlayground={gameState.isPlayground}
                  showAgentPlayButton={SHOW_AGENT_PLAY_IN_REAL_GAMES && !gameState.isPlayground}
                  onViewEventLog={() => setEventLogModalOpen(true)}
                  onAction={(action) => {
                    switch (action) {
                      case 'fold':
                        handlePlayerAction(TexasHoldemAction.FOLD);
                        break;
                      case 'call':
                        if ((renderState?.currentBet ?? 0) === 0) {
                          handlePlayerAction(TexasHoldemAction.CHECK);
                        } else {
                          handlePlayerAction(TexasHoldemAction.CALL);
                        }
                        break;
                      case 'raise':
                        const raiseAmount = (renderState?.currentBet ?? 10) * 2 || 20;
                        handlePlayerAction(TexasHoldemAction.RAISE, raiseAmount);
                        break;
                    }
                  }}
                  onAgentTurn={handleAgentTurn}
                />
              </div>

            ) : (
              <div className="flex items-center justify-center h-full max-h-full p-2">
                <div className="text-center text-white max-w-4xl w-full overflow-y-auto max-h-full">
                  <h2 className="text-3xl font-bold mb-4">Welcome to Texas Hold'em</h2>
                  <p className="mb-8 text-white/80 text-lg">Create a new game or rejoin an existing one to get started.</p>

                  {/* Existing Games Section */}
                  {loadingGames ? (
                    <div className="mb-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                      <p className="text-white/60">Loading your games...</p>
                    </div>
                  ) : userGames.length > 0 ? (
                    <div className="mb-8">
                      <h3 className="text-xl font-semibold mb-4 text-white">Your Active Games</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 justify-center">
                        {userGames.map((game) => {
                          const isFinished = game.state.isFinished;
                          const playerCount = game.state.players.length;
                          const pot = game.state.pot;
                          const bettingRound = PokerUtils.getBettingRoundName(game.state.bettingRound);

                          return (
                            <Card key={game.id} className="bg-white/10 border-white/20 text-white">
                              <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                  <CardTitle className="text-lg text-white">Game {game.id.slice(-8)}</CardTitle>
                                  <Badge
                                    variant={isFinished ? "destructive" : "default"}
                                    className={isFinished ? "" : "bg-green-600"}
                                  >
                                    {isFinished ? 'Finished' : 'Active'}
                                  </Badge>
                                </div>
                              </CardHeader>
                              <CardContent className="space-y-3">
                                <div className="flex justify-between text-sm">
                                  <span className="text-white/70">Players:</span>
                                  <span className="text-white">{playerCount}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                  <span className="text-white/70">Pot:</span>
                                  <span className="text-white">${pot}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                  <span className="text-white/70">Round:</span>
                                  <span className="text-white">{bettingRound}</span>
                                </div>
                                <Button
                                  onClick={() => handleObserveGame(game)}
                                  className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white"
                                  disabled={isFinished}
                                >
                                  {isFinished ? 'Game Finished' : 'Observe'}
                                </Button>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="mb-8 text-center py-8">
                      <p className="text-white/60 mb-4">No active games found.</p>
                      <Button
                        onClick={() => navigate('/games')}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        Find a Match
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Event Log Modal */}
      <SharedModal open={eventLogModalOpen} onOpenChange={setEventLogModalOpen} title="Event Log" size="xl">
        <div className="flex-1 max-h-[70vh] overflow-auto">
          <EventLog events={(gameState?.events || []) as any} maxHeight="60vh" noMargin noCard />
        </div>
      </SharedModal>

      <GameVictoryModal
        open={victoryModalOpen}
        onOpenChange={setVictoryModalOpen}
        isVictory={isVictory}
        gameId={String(gameState?.id || '')}
        gameType="texas-holdem"
        endReason={undefined} // Poker doesn't have forfeit reasons yet
      />
    </div>
  );
};

export default PokerGame;
