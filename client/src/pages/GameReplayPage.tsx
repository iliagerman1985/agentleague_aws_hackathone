import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Loader2, Play, Pause, SkipBack, SkipForward, ArrowLeft, Settings, MessageSquare, BarChart3, Zap, Brain, ListOrdered, Wrench } from 'lucide-react';
import { toast } from 'sonner';
import { ToolCallsModal } from '@/components/common/ToolCallsModal';
import { ChessBoard } from '@/components/chess/ChessBoard';
import ChessClocks from '@/components/games/chess/ChessClocks';
import { EnvironmentBackground } from '@/components/art/EnvironmentBackground';

import { Avatar } from '@/components/common/Avatar';

import { ChessApiService, type GameStateResponse } from '@/services/chessApi';
import { GameApiService } from '@/services/gameApi';

import type { ChessState, ChessStateView } from '@/types/chess';
import type { AgentId, GameId, PlayerId } from '@/types/ids';
import { agentsService } from '@/services/agentsService';
import { AgentProfileModal } from '@/components/common/agent/AgentProfileModal';
import { useAgentProfile } from '@/hooks/useAgentProfile';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/contexts/AuthContext';

const toGameId = (id: string): GameId => id as unknown as GameId;

interface GameReplayPageProps {
  gameId?: string;
  gameType?: string;
}

export const GameReplayPage: React.FC<GameReplayPageProps> = ({ gameId: propGameId, gameType: propGameType }) => {
  const { gameId: routeGameId, gameType: routeGameType } = useParams<{ gameId: string; gameType: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const gameId = propGameId || routeGameId;
  const gameType = propGameType || routeGameType;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [game, setGame] = useState<GameStateResponse | null>(null);
  const [fullGameEvents, setFullGameEvents] = useState<any[]>([]); // Store all events from initial load
  const [moveIndices, setMoveIndices] = useState<number[]>([]); // Event indices that are moves
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0); // Index into moveIndices array (0 = initial position, 1 = after move 1, etc.)
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.5);
  const [agentAvatars, setAgentAvatars] = useState<Record<string, { avatarUrl?: string | null; avatarType?: string }>>({});
  const [agentIdsByPlayerId, setAgentIdsByPlayerId] = useState<Record<string, AgentId>>({});
  const [activeTab, setActiveTab] = useState<"game" | "info">("game");
  const [stateCache, setStateCache] = useState<Map<number, GameStateResponse>>(new Map());
  const { selectedAgentId, isProfileOpen, showAgentProfile, closeAgentProfile } = useAgentProfile();

  // Tool calls modal state
  const [toolCallsModalOpen, setToolCallsModalOpen] = useState<boolean>(false);
  const [selectedToolCalls, setSelectedToolCalls] = useState<any[]>([]);
  const [selectedAgentName, setSelectedAgentName] = useState<string>("");

  // Unread indicator for Info tab
  const [lastSeenInfoCount, setLastSeenInfoCount] = useState(0);

  // Refs for auto-scrolling
  const reasoningScrollRef = useRef<HTMLDivElement>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const movesScrollRef = useRef<HTMLDivElement>(null);
  const analysisScrollRef = useRef<HTMLDivElement>(null);



  // Load initial game data to get total event count
  useEffect(() => {
    const loadInitialData = async () => {
      if (!gameId || gameType !== 'chess') {
        setError('Invalid game or unsupported game type');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);

        // Fetch full game to get total events
        const fullGame = await ChessApiService.getGameState(toGameId(gameId));


        // Store full game events for move list display
        setFullGameEvents(fullGame.events || []);

        // Fetch unfiltered events to build authoritative move indices for backend replay
        const rawEvents = await GameApiService.getEvents(toGameId(gameId));
        const moves: number[] = [];
        rawEvents.forEach((event: any) => {
          const idx = typeof event.eventIndex === 'number' ? event.eventIndex : (typeof event.event_index === 'number' ? event.event_index : undefined);
          if (event.type === 'move_played' && typeof idx === 'number') {
            moves.push(idx);
          }
        });
        setMoveIndices(moves);

        // Load initial state (before any moves)
        if (moves.length > 0) {
          // Load state at the event just before the first move
          // This gives us the initial board position
          const firstMoveIndex = moves[0];
          const initialEventIndex = firstMoveIndex - 1; // Event before first move
          const initialState = await ChessApiService.getStateAtEvent(toGameId(gameId), initialEventIndex);
          setGame(initialState);
          setCurrentMoveIndex(0);

          // Cache the initial state
          setStateCache(new Map([[initialEventIndex, initialState]]));
        } else {
          setGame(fullGame);
          setCurrentMoveIndex(0);
          setStateCache(new Map([[0, fullGame]]));
        }

        // Load agent avatars and IDs using cached service
        if (fullGame.players) {
          const versionIds = fullGame.players
            .map((p: any) => p.agentVersionId)
            .filter(Boolean);

          if (versionIds.length > 0) {
            // Use cached avatar loading
            const avatars = await agentsService.getAgentAvatarsFromVersionIds(versionIds);

            // Map avatars by player ID and get agent IDs
            const avatarMap: Record<string, { avatarUrl?: string | null; avatarType?: string }> = {};
            const agentIdMap: Record<string, AgentId> = {};

            await Promise.all(fullGame.players.map(async (p: any) => {
              const versionId = p.agentVersionId;
              if (versionId && avatars[versionId]) {
                avatarMap[p.id] = avatars[versionId];
              }

              // Get agent ID from version
              if (versionId) {
                try {
                  const agent = await agentsService.getAgentFromVersion(versionId);
                  if (agent) {
                    agentIdMap[p.id] = agent.id as AgentId;
                  }
                } catch {
                  // Agent version not found, skip
                }
              }
            }));

            setAgentAvatars(avatarMap);
            setAgentIdsByPlayerId(agentIdMap);
          }
        }

        setLoading(false);
      } catch (err: any) {
        console.error('Error loading replay data:', err);
        setError(err.message || 'Failed to load replay data');
        setLoading(false);
        toast.error('Failed to load replay data');
      }
    };

    void loadInitialData();
  }, [gameId, gameType]);

  // Load state at current move index with caching
  useEffect(() => {
    const loadStateAtIndex = async () => {
      if (!gameId || moveIndices.length === 0 || currentMoveIndex < 0) return;

      // currentMoveIndex = 0 means initial position (before any moves)
      // currentMoveIndex = 1 means after move 1
      // currentMoveIndex = 2 means after move 2, etc.

      let eventIndex: number;
      if (currentMoveIndex === 0) {
        // Initial position: load state before first move
        eventIndex = moveIndices[0] - 1;
      } else {
        // After move N: load state at move N's event index
        const moveEventIndex = moveIndices[currentMoveIndex - 1];
        if (moveEventIndex === undefined) return;
        eventIndex = moveEventIndex;
      }

      // Check cache first
      if (stateCache.has(eventIndex)) {
        setGame(stateCache.get(eventIndex)!);
        return;
      }

      try {
        const stateAtEvent = await ChessApiService.getStateAtEvent(toGameId(gameId), eventIndex);


        setGame(stateAtEvent);

        // Cache the state
        setStateCache((prev) => {
          const newCache = new Map(prev);
          newCache.set(eventIndex, stateAtEvent);
          return newCache;
        });
      } catch (err: any) {
        console.error('Error loading state at move:', err);
        toast.error('Failed to load game state');
      }
    };

    void loadStateAtIndex();
  }, [gameId, currentMoveIndex, moveIndices, stateCache]);

  // Auto-play functionality - jump between moves
  useEffect(() => {
    // Max index is moveIndices.length (not length - 1) because index 0 is initial position
    if (!isPlaying || currentMoveIndex >= moveIndices.length) {
      if (isPlaying) {
      }
      setIsPlaying(false);
      return;
    }

    const timer = setTimeout(() => {
      setCurrentMoveIndex((prev) => Math.min(prev + 1, moveIndices.length));
    }, playbackSpeed * 1000);

    return () => clearTimeout(timer);
  }, [isPlaying, currentMoveIndex, moveIndices.length, playbackSpeed]);

  const handlePlayPause = useCallback(() => {
    setIsPlaying((prev) => {
      const next = !prev;
      return next;
    });
  }, [isPlaying]);

  const handleStepBackward = useCallback(() => {
    setCurrentMoveIndex((prev) => Math.max(0, prev - 1));
    setIsPlaying(false);
  }, []);

  const handleStepForward = useCallback(() => {
    // Max index is moveIndices.length (not length - 1) because index 0 is initial position
    setCurrentMoveIndex((prev) => Math.min(moveIndices.length, prev + 1));
    setIsPlaying(false);
  }, [moveIndices.length]);

  const handleSliderChange = useCallback((value: number[]) => {
    setCurrentMoveIndex(value[0]);
    setIsPlaying(false);
  }, []);

  const handleBack = useCallback(() => {
    navigate('/games');
  }, [navigate]);

  // Extract move events for display - use fullGameEvents to show all moves
  const moveEvents = useMemo(() => {
    if (!fullGameEvents || fullGameEvents.length === 0) return [];
    const moves = fullGameEvents
      .filter((e: any) => e.type === 'move_played')
      .map((e: any, idx: number) => ({
        id: idx,
        text: `${e.fromSquare} → ${e.toSquare}${e.promotion ? `=${e.promotion.toUpperCase()}` : ''}`,
        fromSquare: e.fromSquare,
        toSquare: e.toSquare,
      }));


    return moves;
  }, [fullGameEvents, moveIndices]);

  // Get all events from start up to current move (cumulative history)
  const eventsUpToCurrentMove = useMemo(() => {
    if (!game?.events || moveIndices.length === 0) return [];

    // Align with board mapping:
    // currentMoveIndex = 0 -> events up to (firstMoveIndex - 1)
    // currentMoveIndex = N -> events up to Nth move's event index
    const endEventIndex = currentMoveIndex === 0
      ? moveIndices[0] - 1
      : moveIndices[currentMoveIndex - 1];

    if (endEventIndex === undefined) return [];

    // Get all events from the beginning up to and including endEventIndex
    return game.events.slice(0, endEventIndex + 1);
  }, [game?.events, moveIndices, currentMoveIndex]);

  // Extract reasoning, chat, and analysis from all events up to current move
  const reasoningEvents = useMemo(() => {
    const filtered = eventsUpToCurrentMove
      .filter((e: any) => e.type === 'agent_reasoning')
      .map((e: any) => ({
        ...e,
        toolCalls: e.tool_calls || [],
      }));


    return filtered;
  }, [eventsUpToCurrentMove]);

  const chatEvents = useMemo(() => {
    return eventsUpToCurrentMove.filter((e: any) => e.type === 'chat_message');
  }, [eventsUpToCurrentMove]);

  const analysisEvents = useMemo(() => {
    return eventsUpToCurrentMove.filter((e: any) => e.type === 'move_analysis');
  }, [eventsUpToCurrentMove]);

  // Calculate total info events for unread indicator
  const totalInfoEvents = useMemo(() => {
    return reasoningEvents.length + chatEvents.length + analysisEvents.length + moveEvents.length;
  }, [reasoningEvents.length, chatEvents.length, analysisEvents.length, moveEvents.length]);

  const unreadInfoCount = Math.max(0, totalInfoEvents - lastSeenInfoCount);

  // Mark info as seen when viewing Info tab
  useEffect(() => {
    if (activeTab === 'info') {
      setLastSeenInfoCount(totalInfoEvents);
    }
  }, [activeTab, totalInfoEvents]);

  // Get player names and ratings - use color field to determine white/black
  const whitePlayer = useMemo(() => {
    return game?.players?.find(p => p.color === 'white') || game?.players?.[0];
  }, [game?.players]);

  const blackPlayer = useMemo(() => {
    return game?.players?.find(p => p.color === 'black') || game?.players?.[1];
  }, [game?.players]);

  const whitePlayerName = (() => {
    if (!whitePlayer) return 'White';
    const agentName = whitePlayer.name || 'White';
    const display = (whitePlayer as any).displayName ?? whitePlayer.username;
    return display ? `${agentName} (${display})` : agentName;
  })();

  const blackPlayerName = (() => {
    if (!blackPlayer) return 'Black';
    const agentName = blackPlayer.name || 'Black';
    const display = (blackPlayer as any).displayName ?? blackPlayer.username;
    return display ? `${agentName} (${display})` : agentName;
  })();

  const whiteRating = whitePlayer?.rating;
  const blackRating = blackPlayer?.rating;
  const whitePlayerId = whitePlayer?.id;
  const blackPlayerId = blackPlayer?.id;

  const renderState: ChessStateView = (game?.state as unknown as ChessState) as unknown as ChessStateView;

  // Log render state for debugging
  useEffect(() => {
    if (renderState) {
    }
  }, [renderState, currentMoveIndex]);

  // Determine current player based on side to move
  const currentPlayerId = useMemo(() => {
    if (!whitePlayerId || !blackPlayerId || !renderState) return whitePlayerId;
    return renderState.sideToMove === 'white' ? whitePlayerId : blackPlayerId;
  }, [whitePlayerId, blackPlayerId, renderState?.sideToMove]);

  // Determine user's color for board orientation in replay mode
  const userColor = useMemo((): 'white' | 'black' => {
    if (!game || !user) return 'white';

    // Check config for userSide (from playground games)
    const configSide = (game.config as Record<string, any> | undefined | null)?.userSide
      ?? (game.config as Record<string, any> | undefined | null)?.user_side;
    if (configSide === 'white' || configSide === 'black') {
      return configSide;
    }

    // For real games, determine which player belongs to the current user
    // Use the color field from player data which is set by the backend
    if (game.players && game.players.length === 2) {
      // Find the player that belongs to the current user
      const userPlayer = game.players.find(p => p.username === user.username);
      if (userPlayer?.color) {
        return userPlayer.color;
      }
    }

    // Default to white if we can't determine
    return 'white';
  }, [game, user]);

  // Initial scroll-to-bottom for all panels when component mounts
  useEffect(() => {
    const els = [
      reasoningScrollRef.current,
      chatScrollRef.current,
      movesScrollRef.current,
      analysisScrollRef.current,
    ].filter(Boolean) as HTMLDivElement[];
    els.forEach((el) => {
      el.scrollTop = el.scrollHeight;
    });
  }, []);

  // Auto-scroll effects for reasoning, chat, moves, and analysis
  useEffect(() => {
    if (reasoningScrollRef.current) {
      reasoningScrollRef.current.scrollTop = reasoningScrollRef.current.scrollHeight;
    }
  }, [reasoningEvents]);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatEvents]);

  useEffect(() => {
    if (movesScrollRef.current) {
      movesScrollRef.current.scrollTop = movesScrollRef.current.scrollHeight;
    }
  }, [moveEvents]);

  useEffect(() => {
    if (analysisScrollRef.current) {
      analysisScrollRef.current.scrollTop = analysisScrollRef.current.scrollHeight;
    }
  }, [analysisEvents]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-brand-teal" />
      </div>
    );
  }

  if (!game || error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <p className="text-muted-foreground">{error || 'No replay data available'}</p>
        <Button onClick={handleBack} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Games
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full h-screen flex flex-col p-2 md:p-4 gap-2 md:gap-4">
      {/* Header with Back button */}
      <div className="relative flex-shrink-0 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
        <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
          <EnvironmentBackground environment="chess" opacity={0.20} />
        </div>
        <div className="relative z-10 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Game Replay</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {currentMoveIndex === 0 ? 'Initial Position' : `Move ${currentMoveIndex} of ${moveIndices.length}`}
            </p>
          </div>
          <Button variant="outline" onClick={handleBack} className="rounded-md">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>
      </div>

      {/* Main content - Desktop: grid layout, Mobile: tabs only */}
      <div className="hidden md:grid min-w-0 flex-1 min-h-0 md:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[280px_minmax(0,1fr)_360px] md:overflow-hidden gap-3">
        {/* Left: Game Analysis and Moves (2xl screens only) */}
        <div className="hidden 2xl:flex 2xl:min-w-0 2xl:flex-col 2xl:gap-3 2xl:h-full 2xl:overflow-hidden pt-1">
          {/* Game Analysis - fills remaining space */}
          <Card className="flex-1 min-h-0 flex flex-col overflow-hidden bg-emerald-50/50 dark:bg-card">
            <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
              <CardTitle className="text-lg flex items-center gap-2">
                <Zap className="w-5 h-5 text-brand-mint" /> Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={analysisScrollRef}>
              {analysisEvents.length > 0 ? (
                <div className="space-y-3">
                  {analysisEvents.map((a: any, idx: number) => (
                    <div key={idx} className="space-y-2 pb-3 border-b last:border-b-0 last:pb-0">
                      <div className="font-medium text-xs">
                        {a.fromSquare} → {a.toSquare}
                      </div>
                      {a.narrative && (
                        <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{a.narrative}</div>
                      )}
                      <div className="flex flex-wrap gap-2 text-xs">
                        {a.bestMoveSan && (<span className="rounded-md bg-muted px-2 py-0.5">Best: {a.bestMoveSan}</span>)}
                        {typeof a.evaluation === 'number' && (<span className="rounded-md bg-muted px-2 py-0.5">Eval: {(a.evaluation/100).toFixed(2)}</span>)}
                        {a.isBrilliant && (<span className="rounded-md bg-brand-mint/20 text-brand-mint px-2 py-0.5">Brilliant</span>)}
                        {a.isGood && (<span className="rounded-md bg-brand-mint/10 text-brand-mint px-2 py-0.5">Good</span>)}
                        {a.isInaccuracy && (<span className="rounded-md bg-amber-100 text-amber-700 px-2 py-0.5">Inaccuracy</span>)}
                        {a.isMistake && (<span className="rounded-md bg-orange-100 text-orange-700 px-2 py-0.5">Mistake</span>)}
                        {a.isBlunder && (<span className="rounded-md bg-red-100 text-red-700 px-2 py-0.5">Blunder</span>)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No analysis yet.</div>
              )}
            </CardContent>
          </Card>

          {/* Moves - fixed height */}
          <Card className="flex-shrink-0 h-[20vh] flex flex-col overflow-hidden bg-orange-50/50 dark:bg-card">
            <CardHeader className="pb-3 flex-shrink-0">
              <CardTitle className="text-lg flex items-center gap-2">
                <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-4 pb-4" ref={movesScrollRef}>
              {moveEvents.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No moves yet.</div>
              ) : (
                <ol className="space-y-1 pl-4 list-decimal text-xs">
                  {moveEvents.map((m, idx) => (
                    <li
                      key={m.id}
                      className={`leading-snug cursor-pointer hover:text-brand-teal transition-colors ${
                        idx + 1 === currentMoveIndex ? 'font-bold text-brand-teal' : ''
                      }`}
                      onClick={() => {
                        setCurrentMoveIndex(idx + 1); // +1 because index 0 is initial position
                        setIsPlaying(false);
                      }}
                    >
                      {m.text}
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Middle: Board and Controls - hidden on mobile, shown on md+ */}
        <div className="hidden md:flex flex-col min-w-0 space-y-2 md:h-full md:overflow-hidden pt-1">
          {/* Chess Board */}
          <Card className="flex-1 min-h-0 overflow-hidden bg-amber-50/30 dark:bg-card">
            <CardContent className="p-0 h-full flex items-center justify-center">
              <ChessBoard
                state={renderState}
                onMoveSelected={undefined}
                hideCapturedPieces={false}
                whitePlayerName={whitePlayerName}
                blackPlayerName={blackPlayerName}
                whiteRating={whiteRating}
                blackRating={blackRating}
                whitePlayerAvatar={whitePlayerId ? agentAvatars[whitePlayerId] : undefined}
                blackPlayerAvatar={blackPlayerId ? agentAvatars[blackPlayerId] : undefined}
                onWhitePlayerClick={whitePlayerId && agentIdsByPlayerId[whitePlayerId] ? () => showAgentProfile(agentIdsByPlayerId[whitePlayerId]) : undefined}
                onBlackPlayerClick={blackPlayerId && agentIdsByPlayerId[blackPlayerId] ? () => showAgentProfile(agentIdsByPlayerId[blackPlayerId]) : undefined}
                flipped={userColor === 'black'}
              />
            </CardContent>
          </Card>

          {/* Replay Controls */}
          <Card className="flex-shrink-0 bg-amber-50/30 dark:bg-card">
            <CardContent className="p-4">
              <div className="flex flex-col gap-4">
                {/* Scrubber */}
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {Math.round((currentMoveIndex / Math.max(1, moveIndices.length)) * 100)}%
                  </span>
                  <Slider
                    value={[currentMoveIndex]}
                    onValueChange={handleSliderChange}
                    max={Math.max(0, moveIndices.length)}
                    step={1}
                    className="flex-1"
                  />
                </div>

                {/* Playback Controls */}
                <div className="flex items-center justify-center gap-2">
                  <Button variant="outline" size="icon" onClick={handleStepBackward} disabled={currentMoveIndex === 0}>
                    <SkipBack className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="icon" onClick={handlePlayPause}>
                    {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </Button>
                  <Button variant="outline" size="icon" onClick={handleStepForward} disabled={currentMoveIndex >= moveIndices.length}>
                    <SkipForward className="h-4 w-4" />
                  </Button>
                  <div className="ml-4 flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Speed:</span>
                    <Slider
                      value={[playbackSpeed]}
                      onValueChange={(v) => setPlaybackSpeed(v[0])}
                      min={0.5}
                      max={3}
                      step={0.5}
                      className="w-24"
                    />
                    <span className="text-sm text-muted-foreground w-12">{playbackSpeed}s</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: Sidebar */}
        <div className="flex flex-col min-w-0 gap-3 md:h-full md:min-h-0 md:overflow-hidden pt-1">
          {/* Desktop: Moves, Chat, Analysis, and Reasoning */}
          <div className="hidden md:flex md:flex-col md:gap-3 md:h-full md:overflow-hidden pt-1">
            {/* Moves - fixed height (hidden on 2xl where it's in left column) */}
            <Card className="2xl:hidden flex-shrink-0 h-[12vh] flex flex-col overflow-hidden bg-orange-50/50 dark:bg-card">
              <CardHeader className="pb-3 flex-shrink-0">
                <CardTitle className="text-lg flex items-center gap-2">
                  <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-4 pb-4" ref={movesScrollRef}>
                {moveEvents.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No moves yet.</div>
                ) : (
                  <ol className="space-y-1 pl-4 list-decimal text-xs">
                    {moveEvents.map((m, idx) => (
                      <li
                        key={m.id}
                        className={`leading-snug cursor-pointer hover:text-brand-teal transition-colors ${
                          idx + 1 === currentMoveIndex ? 'font-bold text-brand-teal' : ''
                        }`}
                        onClick={() => {
                          setCurrentMoveIndex(idx + 1); // +1 because index 0 is initial position
                          setIsPlaying(false);
                        }}
                      >
                        {m.text}
                      </li>
                    ))}
                  </ol>
                )}
              </CardContent>
            </Card>

            {/* Agent Chat - fixed height */}
            <Card className="flex-shrink-0 h-[20vh] flex flex-col overflow-hidden bg-violet-50/50 dark:bg-card">
              <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
                <CardTitle className="text-lg flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-brand-teal" /> Agent Chat
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={chatScrollRef}>
                {chatEvents.length > 0 ? (
                  <div className="space-y-3">
                    {chatEvents.map((c: any, idx: number) => (
                      <div key={idx} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                        <div className="flex items-center gap-2">
                          <Avatar
                            src={c.playerId ? agentAvatars[c.playerId]?.avatarUrl : undefined}
                            fallback={game.players?.find((p: any) => p.id === c.playerId)?.name || 'Agent'}
                            size="sm"
                            className="flex-shrink-0"
                            type={c.playerId ? (agentAvatars[c.playerId]?.avatarType as any) : undefined}
                          />
                          <div className="font-medium text-brand-teal">
                            {game.players?.find((p: any) => p.id === c.playerId)?.name || 'Agent'}
                          </div>
                        </div>
                        <div className="text-muted-foreground whitespace-pre-wrap break-words">{c.message}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No messages yet.</div>
                )}
              </CardContent>
            </Card>

            {/* Game Analysis (hidden on 2xl where it's in left column) - fixed height */}
            <Card className="2xl:hidden flex-shrink-0 h-[20vh] flex flex-col overflow-hidden bg-emerald-50/50 dark:bg-card">
              <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Zap className="w-5 h-5 text-brand-mint" /> Game analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={analysisScrollRef}>
                {analysisEvents.length > 0 ? (
                  <div className="space-y-3">
                    {analysisEvents.map((a: any, idx: number) => (
                      <div key={idx} className="space-y-2 pb-3 border-b last:border-b-0 last:pb-0">
                        <div className="font-medium text-xs">
                          {a.fromSquare} → {a.toSquare}
                        </div>
                        {a.narrative && (
                          <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{a.narrative}</div>
                        )}
                        <div className="flex flex-wrap gap-2 text-xs">
                          {a.bestMoveSan && (<span className="rounded-md bg-muted px-2 py-0.5">Best: {a.bestMoveSan}</span>)}
                          {typeof a.evaluation === 'number' && (<span className="rounded-md bg-muted px-2 py-0.5">Eval: {(a.evaluation/100).toFixed(2)}</span>)}
                          {a.isBrilliant && (<span className="rounded-md bg-brand-mint/20 text-brand-mint px-2 py-0.5">Brilliant</span>)}
                          {a.isGood && (<span className="rounded-md bg-brand-mint/10 text-brand-mint px-2 py-0.5">Good</span>)}
                          {a.isInaccuracy && (<span className="rounded-md bg-amber-100 text-amber-700 px-2 py-0.5">Inaccuracy</span>)}
                          {a.isMistake && (<span className="rounded-md bg-orange-100 text-orange-700 px-2 py-0.5">Mistake</span>)}
                          {a.isBlunder && (<span className="rounded-md bg-red-100 text-red-700 px-2 py-0.5">Blunder</span>)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No analysis yet.</div>
                )}
              </CardContent>
            </Card>

            {/* Reasoning - fills remaining space */}
            <Card className="flex-1 min-h-0 flex flex-col overflow-hidden bg-cyan-50/50 dark:bg-card">
              <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Brain className="w-5 h-5 text-brand-mint" /> Reasoning
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={reasoningScrollRef}>
                {reasoningEvents.length > 0 ? (
                  <div className="space-y-3">
                    {reasoningEvents.map((r: any, idx: number) => (
                      <div key={idx} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                        <div className="flex items-center gap-2">
                          <div
                            className="cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={() => r.playerId && agentIdsByPlayerId[r.playerId] && showAgentProfile(agentIdsByPlayerId[r.playerId])}
                          >
                            <Avatar
                              src={r.playerId ? agentAvatars[r.playerId]?.avatarUrl : undefined}
                              fallback={game.players?.find((p: any) => p.id === r.playerId)?.name || 'Agent'}
                              size="sm"
                              className="flex-shrink-0"
                              type={r.playerId ? (agentAvatars[r.playerId]?.avatarType as any) : undefined}
                            />
                          </div>
                          <div className="font-medium text-brand-teal">
                            {game.players?.find((p: any) => p.id === r.playerId)?.name || 'Agent'}
                          </div>
                        </div>
                        <div className="text-muted-foreground whitespace-pre-wrap break-words">{r.reasoning}</div>
                        {r.toolCalls && r.toolCalls.length > 0 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs mt-1"
                            onClick={() => {
                              setSelectedToolCalls(r.toolCalls);
                              setSelectedAgentName(game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent");
                              setToolCallsModalOpen(true);
                            }}
                          >
                            <Wrench className="w-3 h-3 mr-1" />
                            Tools ({r.toolCalls.length})
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No reasoning yet.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Mobile: Tabs - takes full remaining space */}
      <Card className="md:hidden flex-1 flex flex-col min-h-0 overflow-hidden">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full h-full flex flex-col">
          <CardHeader className="pb-3">
            <TabsList className="grid w-full grid-cols-2 bg-muted p-1">
              <TabsTrigger value="game" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                <Zap className="w-4 h-4 mr-2" />
                Game
              </TabsTrigger>
              <TabsTrigger value="info" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                <Settings className="w-4 h-4 mr-2" />
                Info
                {unreadInfoCount > 0 && (
                  <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-orange px-1 text-[10px] text-white">
                    {unreadInfoCount}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
          </CardHeader>
          <CardContent className="p-0 flex-1 min-h-0 overflow-hidden">
            {/* Game tab: Board and Controls */}
            <TabsContent value="game" className="mt-0 h-full overflow-y-auto">
              <div className="px-2 py-4 space-y-4">
                {/* Show clocks and side to move indicator */}
                {game && renderState && whitePlayerId && blackPlayerId && (
                  <div className="space-y-2">
                    {/* Side to move chip */}
                    <div className="flex justify-center">
                      <div className="glass-chip rounded-app-md px-2 py-0.5 text-[11px] font-medium text-foreground/90 flex items-center gap-2">
                        <span
                          className="inline-block w-2.5 h-2.5 rounded-full"
                          style={{
                            background: renderState.sideToMove === 'white' ? '#F0F2F5' : '#111827',
                            boxShadow: renderState.sideToMove === 'white'
                              ? '0 0 0 1px rgba(0,0,0,.35) inset'
                              : '0 0 0 1px rgba(255,255,255,.35) inset'
                          }}
                          aria-hidden
                        />
                        <span className="uppercase tracking-wide">
                          {renderState.sideToMove === 'white' ? 'White to move' : 'Black to move'}
                        </span>
                      </div>
                    </div>
                    {/* Clocks */}
                    <div className="flex justify-center">
                      <ChessClocks
                        state={renderState}
                        players={[whitePlayerId, blackPlayerId] as [PlayerId, PlayerId]}
                        currentPlayerId={currentPlayerId!}
                      />
                    </div>
                  </div>
                )}
                {/* Chess Board */}
                <div className="flex items-center justify-center">
                  <ChessBoard
                    state={renderState}
                    onMoveSelected={undefined}
                    hideCapturedPieces={false}
                    whitePlayerName={whitePlayerName}
                    blackPlayerName={blackPlayerName}
                    whiteRating={whiteRating}
                    blackRating={blackRating}
                    whitePlayerAvatar={whitePlayerId ? agentAvatars[whitePlayerId] : undefined}
                    blackPlayerAvatar={blackPlayerId ? agentAvatars[blackPlayerId] : undefined}
                    onWhitePlayerClick={whitePlayerId && agentIdsByPlayerId[whitePlayerId] ? () => showAgentProfile(agentIdsByPlayerId[whitePlayerId]) : undefined}
                    onBlackPlayerClick={blackPlayerId && agentIdsByPlayerId[blackPlayerId] ? () => showAgentProfile(agentIdsByPlayerId[blackPlayerId]) : undefined}
                    flipped={userColor === 'black'}
                  />
                </div>

                {/* Replay Controls */}
                <Card>
                  <CardContent className="p-4">
                    <div className="flex flex-col gap-4">
                      {/* Scrubber */}
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground whitespace-nowrap">
                          {Math.round((currentMoveIndex / Math.max(1, moveIndices.length)) * 100)}%
                        </span>
                        <Slider
                          value={[currentMoveIndex]}
                          onValueChange={handleSliderChange}
                          max={Math.max(0, moveIndices.length)}
                          step={1}
                          className="flex-1"
                        />
                      </div>

                      {/* Playback Controls */}
                      <div className="flex items-center justify-center gap-2">
                        <Button variant="outline" size="icon" onClick={handleStepBackward} disabled={currentMoveIndex === 0}>
                          <SkipBack className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="icon" onClick={handlePlayPause}>
                          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </Button>
                        <Button variant="outline" size="icon" onClick={handleStepForward} disabled={currentMoveIndex >= moveIndices.length}>
                          <SkipForward className="h-4 w-4" />
                        </Button>
                      </div>

                      {/* Speed Control */}
                      <div className="flex items-center justify-center gap-2">
                        <span className="text-sm text-muted-foreground">Speed:</span>
                        <Slider
                          value={[playbackSpeed]}
                          onValueChange={(v) => setPlaybackSpeed(v[0])}
                          min={0.5}
                          max={3}
                          step={0.5}
                          className="w-32"
                        />
                        <span className="text-sm text-muted-foreground w-12">{playbackSpeed}s</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Info tab: Moves, Reasoning, Chat, Analysis */}
            <TabsContent value="info" className="mt-0 h-full overflow-y-auto space-y-3 px-4 pb-4">
              {/* Moves */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm pt-0">
                  {moveEvents.length === 0 ? (
                    <div className="text-muted-foreground text-xs">No moves yet.</div>
                  ) : (
                    <ol className="space-y-1 pl-4 list-decimal text-xs max-h-[200px] overflow-y-auto">
                      {moveEvents.map((m, idx) => (
                        <li
                          key={m.id}
                          className={`leading-snug cursor-pointer hover:text-brand-teal transition-colors ${
                            idx + 1 === currentMoveIndex ? 'font-bold text-brand-teal' : ''
                          }`}
                          onClick={() => {
                            setCurrentMoveIndex(idx + 1); // +1 because index 0 is initial position
                            setIsPlaying(false);
                            setActiveTab('game');
                          }}
                        >
                          {m.text}
                        </li>
                      ))}
                    </ol>
                  )}
                </CardContent>
              </Card>

              {/* Reasoning */}
              <Card className="bg-cyan-50/50 dark:bg-card">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Brain className="w-5 h-5 text-brand-mint" /> Reasoning
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm pt-0">
                  {reasoningEvents.length > 0 ? (
                    <div className="space-y-3 max-h-[200px] overflow-y-auto" ref={reasoningScrollRef}>
                      {reasoningEvents.map((r: any, idx: number) => (
                        <div key={idx} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                          <div className="flex items-center gap-2">
                            <Avatar
                              src={r.playerId ? agentAvatars[r.playerId]?.avatarUrl : undefined}
                              fallback={game.players?.find((p: any) => p.id === r.playerId)?.name || 'Agent'}
                              size="sm"
                              className="flex-shrink-0"
                              type={r.playerId ? (agentAvatars[r.playerId]?.avatarType as any) : undefined}
                            />
                            <div className="font-medium text-brand-teal text-xs">
                              {game.players?.find((p: any) => p.id === r.playerId)?.name || 'Agent'}
                            </div>
                          </div>
                          <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs">{r.reasoning}</div>
                          {r.toolCalls && r.toolCalls.length > 0 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs mt-1"
                              onClick={() => {
                                setSelectedToolCalls(r.toolCalls);
                                setSelectedAgentName(game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent");
                                setToolCallsModalOpen(true);
                              }}
                            >
                              <Wrench className="w-3 h-3 mr-1" />
                              Tools ({r.toolCalls.length})
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground text-xs">No reasoning yet.</div>
                  )}
                </CardContent>
              </Card>

              {/* Agent Chat */}
              <Card className="bg-violet-50/50 dark:bg-card">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-brand-teal" /> Agent Chat
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm pt-0">
                  {chatEvents.length > 0 ? (
                    <div className="space-y-3 max-h-[200px] overflow-y-auto" ref={chatScrollRef}>
                      {chatEvents.map((c: any, idx: number) => (
                        <div key={idx} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                          <div className="flex items-center gap-2">
                            <Avatar
                              src={c.playerId ? agentAvatars[c.playerId]?.avatarUrl : undefined}
                              fallback={game.players?.find((p: any) => p.id === c.playerId)?.name || 'Agent'}
                              size="sm"
                              className="flex-shrink-0"
                              type={c.playerId ? (agentAvatars[c.playerId]?.avatarType as any) : undefined}
                            />
                            <div className="font-medium text-brand-teal text-xs">
                              {game.players?.find((p: any) => p.id === c.playerId)?.name || 'Agent'}
                            </div>
                          </div>
                          <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs">{c.message}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground text-xs">No chat messages yet.</div>
                  )}
                </CardContent>
              </Card>

              {/* Analysis */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-brand-orange" /> Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm pt-0">
                  {analysisEvents.length > 0 ? (
                    <div className="space-y-3 max-h-[200px] overflow-y-auto" ref={analysisScrollRef}>
                      {analysisEvents.map((a: any, idx: number) => (
                        <div key={idx} className="space-y-2 pb-3 border-b last:border-b-0 last:pb-0">
                          <div className="font-medium text-xs">
                            {a.fromSquare} → {a.toSquare}
                          </div>
                          {a.evaluation && (
                            <div className="text-xs text-muted-foreground">
                              Eval: {a.evaluation > 0 ? '+' : ''}{(a.evaluation / 100).toFixed(2)}
                            </div>
                          )}
                          {a.narrative && (
                            <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{a.narrative}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground text-xs">No analysis yet.</div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>

      {/* Agent Profile Modal */}
      <AgentProfileModal
        agentId={selectedAgentId}
        open={isProfileOpen}
        onOpenChange={closeAgentProfile}
      />

      {/* Tool Calls Modal */}
      <ToolCallsModal
        open={toolCallsModalOpen}
        onOpenChange={setToolCallsModalOpen}
        toolCalls={selectedToolCalls}
        agentName={selectedAgentName}
      />
    </div>
  );
};

export default GameReplayPage;

