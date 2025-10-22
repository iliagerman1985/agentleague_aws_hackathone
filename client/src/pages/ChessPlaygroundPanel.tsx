import React, { useEffect, useMemo, useRef, useState } from "react";
import { Crown } from "lucide-react";
import { ToolCallsModal } from "@/components/common/ToolCallsModal";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChatWindow } from "@/components/games/ChatWindow";
import { ChessBoard } from "@/components/chess/ChessBoard";
import { AnalysisCard } from "@/components/games/chess/AnalysisCard";
import { ReasoningCard } from "@/components/games/chess/ReasoningCard";
import { MovesCard } from "@/components/games/chess/MovesCard";

import type { ChessMoveData, ChessState, ChessStateView } from "@/types/chess";
import type { AgentId, AgentVersionId, GameId, PlayerId } from "@/types/ids";
import {
  ChessApiService,
  type GameStateResponse,
  type TurnResultResponse,
} from "@/services/chessApi";
import { agentsService } from "@/services/agentsService";

import { useAuth } from "@/contexts/AuthContext";
import { useAgentProfile } from "@/hooks/useAgentProfile";
import { AgentProfileModal } from "@/components/common/agent/AgentProfileModal";

interface Props {
  initialGameId: string;
  onGameEnded?: () => void;
  onReset?: () => void;
}

// Helpers
const toGameId = (id: string): GameId => (id as unknown as GameId);

const toStateView = (s: ChessState): ChessStateView => ({
  board: s.board,
  sideToMove: s.sideToMove,
  castlingRights: s.castlingRights,
  enPassantSquare: s.enPassantSquare,
  halfmoveClock: s.halfmoveClock,
  fullmoveNumber: s.fullmoveNumber,
  remainingTimeMs: s.remainingTimeMs,
  lastTimestampMs: s.lastTimestampMs,
  isFinished: s.isFinished,
  winner: s.winner,
  drawReason: s.drawReason,
  capturedPieces: s.capturedPieces || { white: [], black: [] },
  materialAdvantage: s.materialAdvantage || 0,
});

const ChessPlaygroundPanel: React.FC<Props> = ({ initialGameId, onGameEnded, onReset }) => {
  const [game, setGame] = useState<GameStateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [thinking, setThinking] = useState<boolean>(false);
  const [viewEventIndex, setViewEventIndex] = useState<number | null>(null);
  const [viewState, setViewState] = useState<ChessStateView | null>(null);
  const [playerAvatars, setPlayerAvatars] = useState<Record<string, { avatarUrl?: string | null; avatarType?: string }>>({});
  const [agentIdsByPlayerId, setAgentIdsByPlayerId] = useState<Record<string, AgentId>>({});

  // Tool calls modal state
  const [toolCallsModalOpen, setToolCallsModalOpen] = useState<boolean>(false);
  const [selectedToolCalls, setSelectedToolCalls] = useState<any[]>([]);
  const [selectedAgentName, setSelectedAgentName] = useState<string>("");
  const { updateCoinsBalance } = useAuth();
  const { showAgentProfile, selectedAgentId, isProfileOpen, closeAgentProfile } = useAgentProfile();

  const aliveRef = useRef(true);

  // Auto-scroll refs for Reasoning, Moves, and Analysis (separate per breakpoint)
  const reasoningScrollRef2xl = useRef<HTMLDivElement>(null);
  const reasoningScrollRefMd = useRef<HTMLDivElement>(null);
  const movesScrollRef2xl = useRef<HTMLDivElement>(null);
  const movesScrollRefMd = useRef<HTMLDivElement>(null);
  const analysisScrollRef = useRef<HTMLDivElement>(null);
  const [isReasoningScrolledUp2xl, setIsReasoningScrolledUp2xl] = useState(false);
  const [isReasoningScrolledUpMd, setIsReasoningScrolledUpMd] = useState(false);
  const [isMovesScrolledUp2xl, setIsMovesScrolledUp2xl] = useState(false);
  const [isMovesScrolledUpMd, setIsMovesScrolledUpMd] = useState(false);

  // Track counts for auto-scroll
  const lastReasoningCountRef = useRef(0);
  const lastMovesCountRef = useRef(0);

  // Poll game state: immediate first fetch, then long-poll
  useEffect(() => {
    aliveRef.current = true;
    let currentVersion = 0;

    const poll = async () => {
      while (aliveRef.current) {
        try {
          const g = await ChessApiService.getGameState(toGameId(initialGameId), currentVersion, 25);
          if (!aliveRef.current) return;
          setGame(g);
          currentVersion = g.version ?? 0;
        } catch (e) {
          // On error, wait a bit before retrying
          if (aliveRef.current) {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        }
      }
    };

    const initialLoad = async () => {
      if (!aliveRef.current) return;
      try {
        const g = await ChessApiService.getGameState(toGameId(initialGameId));
        if (!aliveRef.current) return;
        setGame(g);
        currentVersion = g.version ?? 0;
        setLoading(false);
      } catch (e) {
        // ignore and retry into poll loop
      }
      // Start long-polling loop
      void poll();
    };

    void initialLoad();
    return () => {
      aliveRef.current = false;
    };
  }, [initialGameId]);

  // Load avatars when players known
  useEffect(() => {
    const loadAvatars = async () => {
      const players = game?.players as Array<{ id: PlayerId; agentVersionId: AgentVersionId }> | undefined;
      console.log('[ChessPlaygroundPanel] Loading avatars, players:', players);
      if (!players || players.length === 0) return;
      try {
        const versionIds = Array.from(new Set(players.map(p => p.agentVersionId).filter(Boolean)));
        console.log('[ChessPlaygroundPanel] Version IDs:', versionIds);
        if (versionIds.length === 0) return;
        const avatars = await agentsService.getAgentAvatarsFromVersionIdsBatch(versionIds);
        console.log('[ChessPlaygroundPanel] Received avatars (batch):', avatars);
        const mapped: Record<string, { avatarUrl?: string | null; avatarType?: string }> = {};
        players.forEach(p => {
          if (avatars[p.agentVersionId]) {
            mapped[p.id] = avatars[p.agentVersionId];
            console.log(`[ChessPlaygroundPanel] Mapped avatar for player ${p.id}:`, avatars[p.agentVersionId]);
          } else {
            console.warn(`[ChessPlaygroundPanel] No avatar found for player ${p.id} with version ${p.agentVersionId}`);
          }
        });
        console.log('[ChessPlaygroundPanel] Final mapped avatars:', mapped);
        setPlayerAvatars(mapped);

        // Load agent IDs for click handlers via batch
        const idsByVersion = await agentsService.getAgentIdsFromVersionIdsBatch(versionIds);
        const agentIds: Record<string, AgentId> = {} as any;
        for (const p of players) {
          const agentId = idsByVersion[p.agentVersionId as unknown as string];
          if (agentId) {
            agentIds[p.id] = agentId;
          }
        }
        setAgentIdsByPlayerId(agentIds);
      } catch (error) {
        console.error('[ChessPlaygroundPanel] Failed to load avatars:', error);
      }
    };
    void loadAvatars();
  }, [game?.players]);

  // When viewing a past event, fetch reconstructed state
  useEffect(() => {
    const load = async () => {
      if (!game || viewEventIndex === null) { setViewState(null); return; }
      try {
        const res = await ChessApiService.getStateAtEvent(game.id, viewEventIndex);
        const s = res.state as unknown as ChessState;
        setViewState(toStateView(s));
      } catch {
        // ignore
      }
    };
    void load();
  }, [game?.id, viewEventIndex]);

  // Auto-scroll setup for Reasoning (2xl)
  useEffect(() => {
    if (!reasoningScrollRef2xl.current) return;
    const handleScroll = () => {
      const el = reasoningScrollRef2xl.current;
      if (!el) return;
      const { scrollTop, scrollHeight, clientHeight } = el;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50;
      setIsReasoningScrolledUp2xl(!isAtBottom);
    };
    const el = reasoningScrollRef2xl.current;
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  // Auto-scroll setup for Reasoning (md)
  useEffect(() => {
    if (!reasoningScrollRefMd.current) return;
    const handleScroll = () => {
      const el = reasoningScrollRefMd.current;
      if (!el) return;
      const { scrollTop, scrollHeight, clientHeight } = el;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50;
      setIsReasoningScrolledUpMd(!isAtBottom);
    };
    const el = reasoningScrollRefMd.current;
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  // Auto-scroll setup for Moves (2xl)
  useEffect(() => {
    if (!movesScrollRef2xl.current) return;
    const handleScroll = () => {
      const el = movesScrollRef2xl.current;
      if (!el) return;
      const { scrollTop, scrollHeight, clientHeight } = el;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50;
      setIsMovesScrolledUp2xl(!isAtBottom);
    };
    const el = movesScrollRef2xl.current;
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  // Auto-scroll setup for Moves (md)
  useEffect(() => {
    if (!movesScrollRefMd.current) return;
    const handleScroll = () => {
      const el = movesScrollRefMd.current;
      if (!el) return;
      const { scrollTop, scrollHeight, clientHeight } = el;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50;
      setIsMovesScrolledUpMd(!isAtBottom);
    };
    const el = movesScrollRefMd.current;
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);



  const renderState: ChessStateView | null = useMemo(() => {
    if (viewState) return viewState;
    if (!game) return null;
    const s = game.state as ChessState;
    return toStateView(s);
  }, [game?.state, game?.version, viewState]);

  const lastMove = useMemo(() => {
    const evs = (game?.events || []) as any[];
    const last = [...evs].reverse().find((e) => (e.type || e.eventType) === "move_played");
    if (!last) return null;
    const from = last.fromSquare ?? last.from_square ?? last.move?.fromSquare ?? last.move?.from;
    const to = last.toSquare ?? last.to_square ?? last.move?.toSquare ?? last.move?.to;
    return from && to ? { from, to } : null;
  }, [game?.events]);

  const moveEvents = useMemo(() => {
    const evs = (game?.events || []) as any[];
    return evs
      .filter((e) => (e.type || e.eventType) === "move_played")
      .map((e: any, idx: number) => {
        const san = e.move?.san || e.san;
        const from = e.fromSquare ?? e.from_square ?? e.move?.fromSquare ?? e.move?.from;
        const to = e.toSquare ?? e.to_square ?? e.move?.toSquare ?? e.move?.to;
        return { id: e.id || `mv-${idx}` as string, text: san ? san : `${from} → ${to}` };
      });
  }, [game?.events]);

  const reasoningEvents = useMemo(() => {
    const evs = (game?.events || []) as any[];
    return evs
      .filter((e: any) => (e.type || e.eventType) === "agent_reasoning" || (e.type || e.eventType) === "agent_forfeit")
      .map((e: any) => {
        const isForfeit = (e.type || e.eventType) === "agent_forfeit";
        return {
          id: e.id || `reasoning-${e.timestamp}`,
          playerId: e.playerId || e.player_id,
          reasoning: isForfeit
            ? `FORFEIT: ${e.reason || "Failed to move within attempt limit"}`
            : (e.reasoning || e.text || ""),
          timestamp: e.timestamp,
          toolCalls: e.toolCalls || [],
          isForfeit,
        };
      });
  }, [game?.events]);

  const allAnalyses = useMemo(() => {
    const evs = (game?.events || []) as any[];
    return evs
      .filter((e: any) => (e.type || e.eventType) === "move_analysis")
      .map((e: any) => ({
        roundNumber: e.roundNumber,
        moveSan: e.move_san || e.moveSan,
        evaluationCp: e.evaluation_cp ?? e.evaluationCp,
        bestMoveSan: e.best_move_san ?? e.bestMoveSan,
        isBrilliant: e.is_brilliant,
        isGood: e.is_good,
        isInaccuracy: e.is_inaccuracy,
        isMistake: e.is_mistake,
        isBlunder: e.is_blunder,
        narrative: e.narrative,
      }));
  }, [game?.events]);

  // Auto-scroll Reasoning when new items arrive (2xl + md)
  useEffect(() => {
    const hasNewItems = reasoningEvents.length > lastReasoningCountRef.current;
    lastReasoningCountRef.current = reasoningEvents.length;

    if (hasNewItems) {
      if (!isReasoningScrolledUp2xl && reasoningScrollRef2xl.current) {
        reasoningScrollRef2xl.current.scrollTop = reasoningScrollRef2xl.current.scrollHeight;
      }
      if (!isReasoningScrolledUpMd && reasoningScrollRefMd.current) {
        reasoningScrollRefMd.current.scrollTop = reasoningScrollRefMd.current.scrollHeight;
      }
    }
  }, [reasoningEvents, isReasoningScrolledUp2xl, isReasoningScrolledUpMd]);

  // Auto-scroll Moves when new items arrive (2xl + md)
  useEffect(() => {
    const hasNewItems = moveEvents.length > lastMovesCountRef.current;
    lastMovesCountRef.current = moveEvents.length;

    if (hasNewItems) {
      if (!isMovesScrolledUp2xl && movesScrollRef2xl.current) {
        movesScrollRef2xl.current.scrollTop = movesScrollRef2xl.current.scrollHeight;
      }
      if (!isMovesScrolledUpMd && movesScrollRefMd.current) {
        movesScrollRefMd.current.scrollTop = movesScrollRefMd.current.scrollHeight;
      }
    }
  }, [moveEvents, isMovesScrolledUp2xl, isMovesScrolledUpMd]);

  // Auto-scroll Analysis when new items arrive
  useEffect(() => {
    if (analysisScrollRef.current) {
      analysisScrollRef.current.scrollTop = analysisScrollRef.current.scrollHeight;
    }
  }, [allAnalyses]);

  const playerNames = useMemo(() => {
    const names: Record<string, string> = {};
    (game?.players || []).forEach((p: any) => {
      const agentName = p.name;
      const username = p.username;
      names[p.id] = username ? `${agentName} (${username})` : agentName;
    });
    return names;
  }, [game?.players]);
  const playerRatings = useMemo(() => {
    const ratings: Record<string, number | null | undefined> = {};
    (game?.players || []).forEach((p: any) => { ratings[p.id] = p.rating; });
    return ratings;
  }, [game?.players]);

  const whiteBlackIds = useMemo(() => {
    const players = game?.players as Array<{ id: PlayerId }> | undefined;
    if (!players || players.length < 2) return null as unknown as [PlayerId, PlayerId] | null;
    const st = game?.state as ChessState | undefined;
    if (st && st.remainingTimeMs && Object.keys(st.remainingTimeMs).length === 2) {
      const keys = Object.keys(st.remainingTimeMs) as PlayerId[];
      const other = (pid: PlayerId) => (keys[0] === pid ? keys[1] : keys[0]);
      if (st.sideToMove === 'white') return [st.currentPlayerId, other(st.currentPlayerId)];
      return [other(st.currentPlayerId), st.currentPlayerId];
    }
        // fallback to players order
    return [players[0].id as PlayerId, players[1].id as PlayerId];
  }, [game?.players, (game?.state as any)?.remainingTimeMs, (game?.state as any)?.currentPlayerId, (game?.state as any)?.sideToMove]);

  const onMoveSelected = async (move: ChessMoveData) => {
    if (!game) return;
    try {
      const cur = (game.state as ChessState).currentPlayerId as PlayerId;
      const turn = (game.state as ChessState).turn || 0;
      const res: TurnResultResponse = await ChessApiService.executeTurn(game.id, cur, move, turn);
      setGame((prev) => (prev && prev.id === game.id) ? {
        ...prev,
        state: res.newState,
        events: [...prev.events, ...(res.newEvents ?? [])],
        version: (prev.version ?? 0) + 1,
      } : prev);
      // Update coins balance immediately from response
      if (res.newCoinsBalance !== undefined && res.newCoinsBalance !== null) {
        updateCoinsBalance(res.newCoinsBalance);
      }
    } catch (e) {
      // swallow for now; UI will remain
    }
  };

  if (loading || !game || !renderState) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm opacity-70">Loading game…</CardContent>
      </Card>
    );
  }

  return (
    <div className={`grid min-w-0 md:h-[calc(100dvh-260px)] md:max-h-[calc(100dvh-260px)] md:overflow-hidden
      md:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[280px_minmax(0,1fr)_360px] gap-3`}>

      {/* Left: Game Analysis + Moves (2xl only) */}
      <div className="hidden 2xl:flex 2xl:min-w-0 2xl:flex-col 2xl:gap-3 2xl:h-full 2xl:overflow-hidden pt-1">
        <AnalysisCard
          analyses={allAnalyses}
          scrollRef={analysisScrollRef}
          className="flex flex-col overflow-hidden 2xl:flex-1 2xl:min-h-0"
          testId="analysis-card-2xl"
        />
        <MovesCard
          moves={moveEvents}
          scrollRef={movesScrollRef2xl}
          className="flex-shrink-0 h-[12vh] flex flex-col overflow-hidden"
          testId="moves-card-2xl"
        />
      </div>

      {/* Middle: Controls + Board + Analysis */}
      <div className="flex flex-col min-w-0 space-y-2 md:h-full md:overflow-hidden pt-1">
        {/* Controls */}
        <Card className="flex-shrink-0" data-testid="controls-card">
          <CardHeader className="py-1">
            <CardTitle className="text-center text-xs md:text-sm">
              <Crown className="inline-block w-5 h-5 md:w-6 md:h-6 text-yellow-500" />
              <span className="ml-2 align-middle text-[10px] px-1.5 py-0.5 rounded bg-brand-mint/15 text-brand-mint">PlaygroundPanel</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2 p-2 md:p-3">
            <Button size="sm" variant="outline" onClick={() => onReset?.()}>Reset</Button>
            <Button size="sm" variant="outline" onClick={() => {
              if (!game) return;
              const total = game.events?.length ?? 0;
              if (total === 0) return;
              setViewEventIndex((prev) => (prev === null ? total - 1 : Math.max(0, (prev - 1))));
            }}>Back</Button>
            <Button size="sm" variant="outline" onClick={() => {
              if (!game) return;
              setViewEventIndex((prev) => {
                if (prev === null) return null; // already live
                const total = game.events?.length ?? 0;
                const next = prev + 1;
                return next >= total ? null : next; // null => go live
              });
            }} disabled={viewEventIndex === null}>Forward</Button>
            <div className="ml-auto text-[11px] text-muted-foreground hidden md:block">
              {viewEventIndex === null ? 'Live' : `Viewing move ${viewEventIndex + 1} / ${(game?.events?.length ?? 0)}`}
            </div>
            <Button size="sm" variant="destructive" onClick={() => onGameEnded?.()} data-testid="end-game-btn">End Game</Button>
            <Button size="sm" variant="default" className="!bg-brand-teal text-white hover:!bg-brand-teal/90" data-testid="agent-move-btn" disabled={thinking || (renderState?.isFinished ?? false)} onClick={async () => {
              if (!game) return;
              setThinking(true);
              try {
                const cur = (game.state as ChessState).currentPlayerId as PlayerId;
                const turn = (game.state as ChessState).turn || 0;
                const res = await ChessApiService.executeTurn(game.id, cur, null, turn);
                setGame((prev) => (prev && prev.id === game.id) ? { ...prev, state: res.newState, events: [...prev.events, ...(res.newEvents ?? [])], version: (prev.version ?? 0) + 1 } : prev);
                setViewEventIndex(null); // jump back to live after agent move
                // Update coins balance immediately from response
                if (res.newCoinsBalance !== undefined && res.newCoinsBalance !== null) {
                  updateCoinsBalance(res.newCoinsBalance);
                }
              } finally { setThinking(false); }
            }}>Agent Move</Button>
          </CardContent>
        </Card>

        {/* Board */}
        <Card className="flex-1 min-h-0 overflow-hidden bg-amber-50/30 dark:bg-card">
          <CardContent className="p-2 md:p-4 h-full flex items-center justify-center">
            <ChessBoard
              state={renderState}
              onMoveSelected={(renderState.isFinished) ? undefined : onMoveSelected}
              lastMove={lastMove}
              hideCapturedPieces={false}
              whitePlayerName={playerNames[whiteBlackIds?.[0] ?? '']}
              blackPlayerName={playerNames[whiteBlackIds?.[1] ?? '']}
              whiteRating={playerRatings[whiteBlackIds?.[0] ?? '']}
              blackRating={playerRatings[whiteBlackIds?.[1] ?? '']}
              whitePlayerAvatar={playerAvatars[whiteBlackIds?.[0] ?? '']}
              blackPlayerAvatar={playerAvatars[whiteBlackIds?.[1] ?? '']}
              onWhitePlayerClick={whiteBlackIds?.[0] && agentIdsByPlayerId[whiteBlackIds[0]] ? () => {
                showAgentProfile(agentIdsByPlayerId[whiteBlackIds[0]]);
              } : undefined}
              onBlackPlayerClick={whiteBlackIds?.[1] && agentIdsByPlayerId[whiteBlackIds[1]] ? () => {
                showAgentProfile(agentIdsByPlayerId[whiteBlackIds[1]]);
              } : undefined}
            />
          </CardContent>
        </Card>
      </div>

      {/* Right: Moves → Chat → Analysis → Reasoning - hidden on mobile, shown on md+ */}
      <div className="hidden md:flex flex-col min-w-0 gap-3 md:h-full md:min-h-0 md:overflow-hidden pt-1">
        <MovesCard
          moves={moveEvents}
          scrollRef={movesScrollRefMd}
          className="2xl:hidden flex-shrink-0 h-[12vh] flex flex-col overflow-hidden"
          testId="moves-card"
        />

        {/* Agent Chat - takes ~50% of remaining space */}
        <Card className="flex-1 flex flex-col overflow-hidden bg-violet-50/50 dark:bg-card" data-testid="chat-card">
          <ChatWindow
            messages={(game.events || []).filter((e: any) => (e.type || e.eventType) === 'chat_message').map((e: any) => ({
              playerId: e.player_id || e.playerId,
              message: e.message,
              timestamp: e.timestamp,
            }))}
            playerNames={playerNames}
            playerAvatars={playerAvatars}
            onPlayerClick={(playerId) => {
              const agentId = agentIdsByPlayerId[playerId];
              if (agentId) showAgentProfile(agentId);
            }}
          />
        </Card>

        <AnalysisCard
          analyses={allAnalyses}
          scrollRef={analysisScrollRef}
          className="2xl:hidden flex-shrink-0 h-[20vh] flex flex-col overflow-hidden"
          testId="analysis-card-md"
        />

        {/* Reasoning - takes ~50% of remaining space */}
        <ReasoningCard
          reasoningEvents={reasoningEvents}
          playerInfo={Object.fromEntries(
            Object.entries(playerNames).map(([playerId, name]) => [
              playerId,
              {
                name,
                avatarUrl: playerAvatars[playerId]?.avatarUrl,
                avatarType: playerAvatars[playerId]?.avatarType,
              },
            ])
          )}
          onShowAgentProfile={(playerId) => {
            const agentId = agentIdsByPlayerId[playerId];
            if (agentId) showAgentProfile(agentId);
          }}
          onShowToolCalls={(toolCalls, agentName) => {
            setSelectedToolCalls(toolCalls);
            setSelectedAgentName(agentName);
            setToolCallsModalOpen(true);
          }}
          scrollRef={reasoningScrollRefMd}
          className="flex-1 flex flex-col overflow-hidden"
          testId="reasoning-card"
        />
      </div>

      {/* Tool Calls Modal */}
      <ToolCallsModal
        open={toolCallsModalOpen}
        onOpenChange={setToolCallsModalOpen}
        toolCalls={selectedToolCalls}
        agentName={selectedAgentName}
      />
      
      {/* Agent Profile Modal */}
      <AgentProfileModal
        agentId={selectedAgentId}
        open={isProfileOpen}
        onOpenChange={closeAgentProfile}
      />
    </div>
  );
};

export default ChessPlaygroundPanel;

