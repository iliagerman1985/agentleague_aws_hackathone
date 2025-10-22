import React, { useEffect, useMemo, useState } from "react";
import { useMediaQuery } from '@/hooks/useMediaQuery';
// import { useNavigate } from "react-router-dom";
import { type AgentVersionResponse, GameEnvironment } from "@/services/agentsService";
import { type AgentId } from "@/types/ids";



import { ChessApiService, type ChessPlaygroundOpponent, type ChessSide, type GameStateResponse as ChessGameStateResponse } from "@/services/chessApi";
import { PokerApiService } from "@/services/pokerApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChatWindow } from "@/components/games/ChatWindow";

import { Settings, Activity, Brain, ListOrdered } from "lucide-react";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { GameStateManager } from "../components/GameStateManager";
import { GameApiService, GameConfigOptionsResponse } from "@/services/gameApi";
import { GameStatePreview } from "../../../games/GameStatePreview";
import ChessPlaygroundView from '@/pages/ChessPlaygroundView';
import PokerGame from '@/pages/PokerGame';



interface AgentRunTabProps {
  agentId: AgentId;
  activeVersion: AgentVersionResponse;
  gameEnvironment: GameEnvironment;
}




export const AgentRunTab: React.FC<AgentRunTabProps> = ({ agentId, activeVersion, gameEnvironment }) => {
  const [gameStateJson, setGameStateJson] = useState<string>("");
  const [running, setRunning] = useState(false);

  const [iteration, setIteration] = useState(0);
  const [maxIterations] = useState(3);

  // const navigate = useNavigate();

  // Game state management
  const [gameStarted, setGameStarted] = useState(false);
  const [startingGame, setStartingGame] = useState(false);
  const [pokerNumPlayers, setPokerNumPlayers] = useState<number>(5);
  const [createError, setCreateError] = useState<string | null>(null);

  const [mobileTab, setMobileTab] = useState<'info' | 'game'>('game');

  // Inline playground game id
  const [inlineGameId, setInlineGameId] = useState<string | null>(null);

  // Track initial state when game starts for reset functionality
  const [initialGameStateJson, setInitialGameStateJson] = useState<string>("");

  // Match Tailwind md breakpoint which is configured at 1200px
  const isMdUp = useMediaQuery('(min-width: 1200px)');

  // Cleanup current inline playground game (optionally using keepalive for unload)
  // Lightweight data for Info tab (mobile): events and players for chat/moves/analysis
  type InfoPlayer = { id: string; name?: string; rating?: number };
  type InfoData = { events: any[]; players?: InfoPlayer[] } | null;
  const [infoData, setInfoData] = useState<InfoData>(null);
  const [chessOpponent, setChessOpponent] = useState<ChessPlaygroundOpponent>('brain');
  const [chessUserSide, setChessUserSide] = useState<ChessSide>('white');

  // Info tab unread indicator
  const INFO_EVENT_TYPES = new Set<string>(['chat_message','move_played','player_action','move_analysis','agent_reasoning']);
  const [infoLastSeenCount, setInfoLastSeenCount] = useState(0);
  const infoTotalCount = useMemo(() => {
    const evs = infoData?.events || [];
    return evs.filter((e: any) => INFO_EVENT_TYPES.has(e.type)).length;
  }, [infoData]);
  const infoUnreadCount = Math.max(0, infoTotalCount - infoLastSeenCount);

  // When user views Info tab, mark all as seen
  useEffect(() => {
    if (mobileTab === 'info') {
      setInfoLastSeenCount(infoTotalCount);
    }
  }, [mobileTab, infoTotalCount]);

  // Reset unread tracking when a new inline game starts
  useEffect(() => {
    setInfoLastSeenCount(0);
  }, [inlineGameId]);

  // Long-poll game data for Info tab (and to power unread indicator) whenever a game is running
  useEffect(() => {
    if (!inlineGameId || !gameStarted) {
      return;
    }
    let alive = true;
    let currentVersion = 0;

    const longPoll = async () => {
      while (alive) {
        try {
          if (!inlineGameId) return;
          if (gameEnvironment === GameEnvironment.CHESS) {
            const g = await ChessApiService.getGameState(inlineGameId as any, currentVersion, 25);
            if (!alive) return;
            setInfoData({ events: (g as any).events || [], players: (g as any).players || [] });
            setChessOpponent(prev => {
              const inferred = inferOpponentFromGame(g as ChessGameStateResponse | null);
              return prev === inferred ? prev : inferred;
            });
            currentVersion = g.version ?? 0;
          } else {
            const g = await PokerApiService.getGameState(inlineGameId as any, currentVersion, 25);
            if (!alive) return;
            setInfoData({ events: (g as any).events || [], players: (g as any).players || [] });
            currentVersion = g.version ?? 0;
          }
        } catch (e) {
          // On error, wait before retrying
          if (alive) {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        }
      }
    };

    void longPoll();
    return () => { alive = false; };
  }, [inlineGameId, gameStarted, gameEnvironment]);

  const inferOpponentFromGame = (game: ChessGameStateResponse | null): ChessPlaygroundOpponent => {
    if (!game) return 'brain';
    const configOpponent = (game?.config as any)?.playgroundOpponent ?? (game?.config as any)?.playground_opponent;
    if (configOpponent === 'self' || configOpponent === 'brain') {
      return configOpponent;
    }
    const players = (game?.players || []) as Array<{ agentVersionId?: string }>;
    if (players.length === 2 && players[0]?.agentVersionId && players[0]?.agentVersionId === players[1]?.agentVersionId) {
      return 'self';
    }
    return 'brain';
  };

  const cleanupCurrentGame = async (keepalive = false) => {
    try {
      if (inlineGameId) {
        await GameApiService.deleteGame(inlineGameId as any, { keepalive });
        setInlineGameId(null);
      }
    } catch (_) {
      // Swallow cleanup errors
    }
  };

  // Cleanup current playground on unmount/navigation away
  useEffect(() => {
    return () => {
      void cleanupCurrentGame(true);
    };
  }, []);


  // Cleanup current playground on unmount/navigation away
  useEffect(() => {
    return () => {
      void cleanupCurrentGame(true);
    };
  }, []);



  // Game configuration state - loaded from backend
  // We only need resolved default config; no need to store options value separately
  const [gameConfig, setGameConfig] = useState<Record<string, any>>({});
  // Local helpers to mutate config for current environment
  const updateCurrentConfig = (patch: Record<string, any>) => {
    setGameConfig(prev => ({
      ...prev,
      [gameEnvironment]: {
        ...(prev[gameEnvironment] || {}),
        ...patch,
      }
    }));
  };

  // Load game configuration options on mount
  useEffect(() => {
    const loadConfigOptions = async () => {
      try {
        const options = await GameApiService.getConfigOptions();
        if (!options) {
          console.error('[AgentRunTab] Config options is null/undefined');
          return;
        }
        // Initialize game config with defaults
        const initialConfig: Record<string, any> = {};
        if (options && typeof options === 'object' && !Array.isArray(options)) {
          try {
            Object.entries(options).forEach(([gameType, config]) => {
              if (config && typeof config === 'object' && (config as GameConfigOptionsResponse).defaultConfig) {
                initialConfig[gameType] = { ...(config as GameConfigOptionsResponse).defaultConfig };
              }
            });
          } catch (error) {
            console.error('[AgentRunTab] Error processing config options:', error);
          }
        } else {
          console.error('[AgentRunTab] Invalid options format:', typeof options, options);
        }
        setGameConfig(initialConfig);
      } catch (error) {
        console.error('Failed to load game config options:', error);
      }
    };

    void loadConfigOptions();
  }, []);

  // Helper function to update game configuration
  // No interactive config controls here; config is consumed when creating a playground

  // Get current game configuration with fallbacks
  const getCurrentGameConfig = (gameType: string) => {
    if (gameConfig[gameType]) {
      return gameConfig[gameType];
    }

    // Fallback configurations
    if (gameType === GameEnvironment.CHESS) {
      return { time_control: 'long', min_players: 2, max_players: 2 };
    } else if (gameType === GameEnvironment.TEXAS_HOLDEM) {
      return { small_blind: 10, big_blind: 20, starting_chips: 1000, min_players: 2, max_players: 5 };
    }

    return {};
  };

  // Start Game function - creates actual backend playground from loaded state
  const handleStartGame = async () => {
    if (gameStarted || startingGame) return;

    setStartingGame(true);
    setCreateError(null);

    try {
      // Save the initial state before starting the game
      setInitialGameStateJson(gameStateJson);

      const cfg = getCurrentGameConfig(gameEnvironment) || {};
      let resp;

      // Parse the loaded game state
      let loadedState: Record<string, any> | null = null;
      if (gameStateJson.trim()) {
        try {
          loadedState = JSON.parse(gameStateJson);
        } catch {
          // Invalid JSON, will create default game
        }
      }

      const hasLoadedState = loadedState && typeof loadedState === 'object' && Object.keys(loadedState).length > 0;

      if (gameEnvironment === GameEnvironment.TEXAS_HOLDEM) {
        if (hasLoadedState && loadedState) {
          // Create from loaded state
          resp = await PokerApiService.createPlaygroundFromState({
            agentId: activeVersion.id,
            stateView: loadedState,
            numPlayers: pokerNumPlayers,
            config: {
              smallBlind: Number(cfg.small_blind ?? cfg.smallBlind ?? 10),
              bigBlind: Number(cfg.big_blind ?? cfg.bigBlind ?? 20),
              startingChips: Number(cfg.starting_chips ?? cfg.startingChips ?? 1000),
            },
          });
        } else {
          // Create default playground
          resp = await PokerApiService.createPlayground({
            agentId: activeVersion.id,
            config: {
              smallBlind: Number(cfg.small_blind ?? cfg.smallBlind ?? 10),
              bigBlind: Number(cfg.big_blind ?? cfg.bigBlind ?? 20),
              startingChips: Number(cfg.starting_chips ?? cfg.startingChips ?? 1000),
            },
            numPlayers: pokerNumPlayers,
          });
        }
        setInlineGameId(String(resp.id));
      } else if (gameEnvironment === GameEnvironment.CHESS) {
        if (hasLoadedState && loadedState) {
          // Create from loaded state
          resp = await ChessApiService.createPlaygroundFromState({
            agentId: activeVersion.id,
            stateView: loadedState,
            config: { ...cfg, playgroundOpponent: chessOpponent },
            opponent: chessOpponent,
            userSide: chessOpponent === 'brain' ? chessUserSide : undefined,
          });
        } else {
          // Create default playground
          resp = await ChessApiService.createPlayground({
            agentId: activeVersion.id,
            config: { ...cfg, playgroundOpponent: chessOpponent },
            opponent: chessOpponent,
            userSide: chessOpponent === 'brain' ? chessUserSide : undefined,
          });
        }
        setInlineGameId(String(resp.id));
        setChessOpponent(inferOpponentFromGame(resp as ChessGameStateResponse));
      }

      setGameStarted(true);
      setMobileTab('game');
    } catch (e: any) {
      setCreateError(String(e?.message ?? e));
    } finally {
      setStartingGame(false);
    }
  };

  // End Game function - deletes backend playground and resets to preview
  const handleEndGame = async () => {
    if (!gameStarted) return;

    await cleanupCurrentGame();
    setGameStarted(false);
    setRunning(false);
    setIteration(0);
    setInitialGameStateJson(""); // Clear initial state
    setGameStateJson(JSON.stringify({}, null, 2)); // Reset to empty state
  };

  // Reset Game function - restores to initial state that the game started with
  const handleResetGame = async () => {
    if (!gameStarted || !initialGameStateJson) return;

    try {
      // Parse and reload the initial state
      const initialState = JSON.parse(initialGameStateJson);
      await handleLoadGameState(initialState);
    } catch (e: any) {
      setCreateError(String(e?.message ?? e));
    }
  };

  // Initialize with empty state
  useEffect(() => {
    // Set empty initial JSON
    setGameStateJson(JSON.stringify({}, null, 2));
  }, [agentId]);









  const handleLoadGameState = async (newGameState: Record<string, any>, _description?: string) => {
    setGameStateJson(JSON.stringify(newGameState, null, 2));
    setIteration(0);
    setRunning(false);
    setCreateError(null);
    try {
      if (gameEnvironment === GameEnvironment.TEXAS_HOLDEM) {
        const cfg = getCurrentGameConfig(GameEnvironment.TEXAS_HOLDEM) || {};
        // If empty object, create default playground instead of from_state
        const isEmpty = newGameState && typeof newGameState === 'object' && Object.keys(newGameState).length === 0;
        await cleanupCurrentGame();
        if (isEmpty) {
          const resp = await PokerApiService.createPlayground({
            agentId: activeVersion.id,
            config: {
              smallBlind: Number(cfg.small_blind ?? cfg.smallBlind ?? 10),
              bigBlind: Number(cfg.big_blind ?? cfg.bigBlind ?? 20),
              startingChips: Number(cfg.starting_chips ?? cfg.startingChips ?? 1000),
            },
            numPlayers: pokerNumPlayers,
          });
          setInlineGameId(String(resp.id));
        } else {
          const resp = await PokerApiService.createPlaygroundFromState({
            agentId: activeVersion.id,
            stateView: newGameState,
            numPlayers: pokerNumPlayers,
            config: {
              smallBlind: Number(cfg.small_blind ?? cfg.smallBlind ?? 10),
              bigBlind: Number(cfg.big_blind ?? cfg.bigBlind ?? 20),
              startingChips: Number(cfg.starting_chips ?? cfg.startingChips ?? 1000),
            }
          });
          setInlineGameId(String(resp.id));
        }
      } else {
        const cfg = getCurrentGameConfig(GameEnvironment.CHESS) || {};
        await cleanupCurrentGame();
        const resp = await ChessApiService.createPlaygroundFromState({
          agentId: activeVersion.id,
          stateView: newGameState,
          config: { ...cfg, playgroundOpponent: chessOpponent },
          opponent: chessOpponent,
        });
        setInlineGameId(String(resp.id));
        setChessOpponent(inferOpponentFromGame(resp as ChessGameStateResponse));
      }
      setGameStarted(true);
      setMobileTab('game');
    } catch (e: any) {
      setCreateError(String(e?.message ?? e));
    }
  };



  return (
    <div className="h-full flex flex-col">
      {/* Mobile tab selector - only visible on mobile */}
      <div className="md:hidden mb-4">
        <div className="flex items-center gap-2 bg-muted p-1 rounded-lg">
          <Button
            variant={mobileTab === 'game' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1"
            onClick={() => setMobileTab('game')}
            data-testid="m-tab-game"
          >
            <Activity className="h-4 w-4 mr-2" />
            Game
          </Button>
          <Button
            variant={mobileTab === 'info' ? 'default' : 'ghost'}
            size="sm"
            className="flex-1"
            onClick={() => setMobileTab('info')}
            data-testid="m-tab-info"
          >
            <Settings className="h-4 w-4 mr-2" />
            <span className="flex items-center gap-2">
              Info
              {infoUnreadCount > 0 && mobileTab !== 'info' && (
                <span className="inline-flex h-2 w-2 rounded-full bg-brand-orange" aria-hidden="true" />
              )}
            </span>
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 md:h-full overflow-y-auto md:overflow-hidden pt-0 pb-0">
        <div className="space-y-4 relative overflow-hidden">
          <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
          {/* Game Area - Active Game or Preview */}
          {(mobileTab === 'game' || typeof window === 'undefined' || isMdUp) && (
            <div>
              {gameStarted && inlineGameId ? (
                // Active game with backend
                gameEnvironment === GameEnvironment.CHESS ? (
                  <ChessPlaygroundView
                    initialGameId={inlineGameId}
                    onGameEnded={handleEndGame}
                    onReset={handleResetGame}
                  />
                ) : (
                  <PokerGame
                    initialGameId={inlineGameId}
                    isEmbedded={true}
                    onReset={handleResetGame}
                  />
                )
              ) : (
                // Preview mode - show board/table without backend game
                <div className="space-y-3">
                  {/* Header section - more compact */}
                  <div>
                    <h3 className="text-lg font-semibold text-foreground mb-1">Preview Mode</h3>
                    <p className="text-sm text-muted-foreground">
                      {gameStateJson.trim() ?
                        "Configure settings and click 'Start Game' to begin." :
                        "Configure your game settings and click 'Start Game' to begin."
                      }
                    </p>
                  </div>

                  {/* Error banner */}
                  {createError && (
                    <div className="text-sm text-destructive border border-destructive/40 bg-destructive/10 rounded-lg p-2">
                      {createError}
                    </div>
                  )}

                  {/* Two-column layout: Board on left, Configuration on right */}
                  <div className="w-full flex justify-center">
                    <div className="max-w-7xl w-full px-4">
                      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr,1fr] gap-6 items-start">
                        {/* Left Column: Game Preview Visual - Centered */}
                        <div className="flex items-center justify-center w-full">
                          <div className="w-full max-w-[700px] mx-auto">
                            <GameStatePreview
                              environment={gameEnvironment}
                              jsonText={gameStateJson || '{}'}
                              onJsonChange={setGameStateJson}
                              editable={!gameStarted}
                              hideCapturedPieces
                            />
                          </div>
                        </div>

                        {/* Right Column: Game Configuration Section */}
                        <Card className="relative overflow-hidden w-full">
                          <EnvironmentBackground environment={gameEnvironment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
                          <CardHeader className="pb-3">
                            <CardTitle className="text-base">Game Configuration</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                      {/* Poker Configuration */}
                      {gameEnvironment === GameEnvironment.TEXAS_HOLDEM && (
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-foreground">Small Blind</label>
                            <Input
                              type="number"
                              value={Number((getCurrentGameConfig(GameEnvironment.TEXAS_HOLDEM) as any).small_blind ?? 10)}
                              onChange={(e) => updateCurrentConfig({ small_blind: Number(e.target.value || 0) })}
                              disabled={gameStarted}
                              className="rounded-lg h-9"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-foreground">Big Blind</label>
                            <Input
                              type="number"
                              value={Number((getCurrentGameConfig(GameEnvironment.TEXAS_HOLDEM) as any).big_blind ?? 20)}
                              onChange={(e) => updateCurrentConfig({ big_blind: Number(e.target.value || 0) })}
                              disabled={gameStarted}
                              className="rounded-lg h-9"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-foreground">Starting Chips</label>
                            <Input
                              type="number"
                              value={Number((getCurrentGameConfig(GameEnvironment.TEXAS_HOLDEM) as any).starting_chips ?? 1000)}
                              onChange={(e) => updateCurrentConfig({ starting_chips: Number(e.target.value || 0) })}
                              disabled={gameStarted}
                              className="rounded-lg h-9"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-foreground">Players</label>
                            <Input
                              type="number"
                              min={2}
                              max={9}
                              value={pokerNumPlayers}
                              onChange={(e) => setPokerNumPlayers(Math.max(2, Math.min(9, parseInt(e.target.value || '5'))))}
                              disabled={gameStarted}
                              className="rounded-lg h-9"
                            />
                          </div>
                        </div>
                      )}

                      {/* Chess Configuration */}
                      {gameEnvironment === GameEnvironment.CHESS && (
                        <div className="space-y-3">
                          {/* Opponent Selection */}
                          <div className="space-y-1.5">
                            <label className="text-xs font-medium text-foreground">Select Opponent</label>
                            <div className="flex gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant={chessOpponent === 'brain' ? 'default' : 'outline'}
                                onClick={() => setChessOpponent('brain')}
                                data-testid="agent-run-chess-opponent-brain"
                                disabled={gameStarted}
                                className="rounded-lg flex-1"
                              >
                                Stockfish Bot
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant={chessOpponent === 'self' ? 'default' : 'outline'}
                                onClick={() => setChessOpponent('self')}
                                data-testid="agent-run-chess-opponent-self"
                                disabled={gameStarted}
                                className="rounded-lg flex-1"
                              >
                                Self-Play
                              </Button>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {chessOpponent === 'brain'
                                ? 'Train against the Stockfish-powered Brain opponent.'
                                : 'Control both sides yourself to analyze ideas without bot moves.'}
                            </p>
                          </div>

                          {/* Side selection - only show when playing against Brain bot */}
                          {chessOpponent === 'brain' && (
                            <div className="space-y-1.5">
                              <label className="text-xs font-medium text-foreground">Choose Your Side</label>
                              <div className="flex gap-2">
                                <Button
                                  type="button"
                                  size="sm"
                                  variant={chessUserSide === 'white' ? 'default' : 'outline'}
                                  onClick={() => setChessUserSide('white')}
                                  data-testid="agent-run-chess-side-white"
                                  disabled={gameStarted}
                                  className="rounded-lg flex-1"
                                >
                                  ♔ White
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant={chessUserSide === 'black' ? 'default' : 'outline'}
                                  onClick={() => setChessUserSide('black')}
                                  data-testid="agent-run-chess-side-black"
                                  disabled={gameStarted}
                                  className="rounded-lg flex-1"
                                >
                                  ♚ Black
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Save/Load State Management */}
                      <div className="pt-3 border-t border-border">
                        <div className="mb-3">
                          <label className="text-xs font-medium text-foreground block mb-1">Game State</label>
                          <p className="text-xs text-muted-foreground">
                            Save custom positions or load predefined scenarios to test your agent in specific situations instead of starting from the initial position.
                          </p>
                        </div>
                        <GameStateManager
                          agentId={agentId}
                          gameState={(() => {
                            try {
                              return gameStateJson ? JSON.parse(gameStateJson) : {};
                            } catch {
                              return {};
                            }
                          })()}
                          onLoadState={handleLoadGameState}
                          iterationCount={iteration}
                          maxIterations={maxIterations}
                          running={running}
                          environment={gameEnvironment}
                        />
                      </div>

                        {/* Start/End Game Button - Inside card */}
                        <div className="flex justify-center pt-2">
                          {!gameStarted ? (
                            <Button
                              onClick={handleStartGame}
                              disabled={startingGame}
                              size="default"
                              className="w-full rounded-lg"
                            >
                              {startingGame ? 'Starting Game...' : 'Start Game'}
                            </Button>
                          ) : (
                            <Button
                              onClick={handleEndGame}
                              variant="destructive"
                              size="default"
                              className="w-full rounded-lg"
                            >
                              End Game
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Info Panel (mobile only): moves + analysis + chat */}
          {mobileTab === 'info' && gameStarted && inlineGameId && (
            <div className="space-y-4 md:hidden">
              {/* Insights: Moves and Analysis */}
              <div className="flex flex-col gap-4">
               

                {/* Moves */}
                <Card className="flex-shrink-0">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 max-h-[150px] overflow-y-auto">
                    {(() => {
                      const evs: any[] = infoData?.events || [];
                      let items: string[] = [];
                      if (gameEnvironment === GameEnvironment.CHESS) {
                        items = evs
                          .filter((e: any) => e.type === 'move_played')
                          .map((e: any) => `${e.fromSquare} \u2192 ${e.toSquare}${e.promotion ? `=${String(e.promotion).toUpperCase()}` : ''}`);
                      } else {
                        // Poker: show player actions as moves
                        items = evs
                          .filter((e: any) => e.type === 'player_action')
                          .map((e: any) => {
                            const name = (infoData?.players || []).find(p => p.id === (e.playerId || e.player_id))?.name || 'Player';
                            const amt = typeof e.amount === 'number' ? ` ${e.amount}` : '';
                            return `${name} ${e.action}${amt}`;
                          });
                      }
                      return items.length === 0 ? (
                        <div className="text-xs text-muted-foreground">No moves yet.</div>
                      ) : (
                        <ol className="text-xs space-y-1 pl-4 list-decimal">
                          {items.map((t, idx) => (
                            <li key={idx} className="leading-snug">{t}</li>
                          ))}
                        </ol>
                      );
                    })()}
                  </CardContent>
                </Card>

                {/* Analysis */}
                <Card className="flex-shrink-0">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Brain className="w-5 h-5 text-brand-mint" /> Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 text-sm max-h-[260px] overflow-y-auto">
                    {(() => {
                      const evs: any[] = infoData?.events || [];
                      if (gameEnvironment === GameEnvironment.CHESS) {
                        const analyses = evs.filter((e: any) => e.type === 'move_analysis');
                        if (analyses.length === 0) return <div className="text-xs text-muted-foreground">No analysis yet.</div>;
                        return (
                          <div className="space-y-3">
                            {analyses.map((e: any, idx: number) => (
                              <div key={idx} className="space-y-1">
                                <div className="font-medium text-xs">Move {e.roundNumber}: {e.moveSan || e.move_san}</div>
                                <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{e.narrative}</div>
                              </div>
                            ))}
                          </div>
                        );
                      } else {
                        const reasons = evs.filter((e: any) => e.type === 'agent_reasoning');
                        if (reasons.length === 0) return <div className="text-xs text-muted-foreground">No analysis yet.</div>;
                        return (
                          <div className="space-y-3">
                            {reasons.map((e: any, idx: number) => (
                              <div key={idx} className="space-y-1">
                                <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{String(e.reasoning || e.content || e.details || '')}</div>
                              </div>
                            ))}
                          </div>
                        );
                      }
                    })()}
                  </CardContent>
                </Card>
              </div>

              {/* Chat (last) */}
              <Card className="flex-1 min-h-0 flex flex-col">
                <ChatWindow
                  messages={(infoData?.events || [])
                    .filter((e: any) => e.type === 'chat_message')
                    .map((e: any) => ({
                      playerId: e.playerId || e.player_id,
                      message: e.message,
                      timestamp: e.timestamp,
                    }))}
                  playerNames={(infoData?.players || []).reduce((acc: Record<string, string>, p) => {
                    acc[p.id] = p.name || `Player ${p.id.slice(0, 8)}`;
                    return acc;
                  }, {})}
                />
              </Card>

            </div>
          )}


        </div>
      </div>
    </div>
  );
};

export default AgentRunTab;

