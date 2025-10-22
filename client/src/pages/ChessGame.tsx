import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ChessClocks from '@/components/games/chess/ChessClocks';
import { ChessBoard, ChessPieceView } from '@/components/chess';

import type { ChessMoveData, ChessState, ChessStateView } from '@/types/chess';
import type { AgentId, AgentVersionId, GameId, PlayerId } from '@/types/ids';
import { ChessApiService, type ChessPlaygroundOpponent, type ChessSide, type GameStateResponse, type TurnResultResponse } from '@/services/chessApi';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { EventLog } from '@/components/games/EventLog';
import { ChatWindow } from '@/components/games/ChatWindow';
import { SharedModal } from '@/components/common/SharedModal';
import { ToolCallsModal } from '@/components/common/ToolCallsModal';
import { AnalysisCard } from '@/components/games/chess/AnalysisCard';
import { ReasoningCard } from '@/components/games/chess/ReasoningCard';
import { MovesCard } from '@/components/games/chess/MovesCard';

import { Crown, Settings, Zap, Brain, ListOrdered, Wrench } from "lucide-react";
import { Avatar } from "@/components/common/Avatar";

import { useStateHistory } from '@/hooks/useStateHistory';
import { agentsService } from '@/services/agentsService';
import { AgentProfileModal } from '@/components/common/agent/AgentProfileModal';
import { useAgentProfile } from '@/hooks/useAgentProfile';
import { useAuth } from '@/contexts/AuthContext';
import { GameVictoryModal } from '@/components/games/GameVictoryModal';
// TEMPORARY: Show agent play button in real games (not just playground)
// Set to false to hide the button, or comment out the entire line to remove the feature
const SHOW_AGENT_PLAY_IN_REAL_GAMES = false;

const toGameId = (id: string): GameId => id as unknown as GameId;

const inferPlaygroundOpponent = (g: GameStateResponse | null): ChessPlaygroundOpponent => {
  if (!g) {
    return 'brain';
  }
  const configOpponent = (g.config as Record<string, any> | undefined | null)?.playgroundOpponent
    ?? (g.config as Record<string, any> | undefined | null)?.playground_opponent;
  if (configOpponent === 'self' || configOpponent === 'brain') {
    return configOpponent;
  }
  const players = g.players ?? [];
  if (players.length === 2 && players[0]?.agentVersionId && players[0]?.agentVersionId === players[1]?.agentVersionId) {
    return 'self';
  }
  return 'brain';
};

const inferUserSide = (g: GameStateResponse | null): ChessSide => {
  if (!g) {
    return 'white';
  }
  const configSide = (g.config as Record<string, any> | undefined | null)?.userSide
    ?? (g.config as Record<string, any> | undefined | null)?.user_side;
  if (configSide === 'white' || configSide === 'black') {
    return configSide;
  }
  return 'white';
};

/**
 * Determines the game result from the user's perspective
 */
const getGameResult = (game: GameStateResponse, currentUserId?: PlayerId): { text: string; variant: 'default' | 'success' | 'destructive' } => {
  const state = game.state as ChessState;

  if (!state.isFinished) {
    return { text: 'In Progress', variant: 'default' };
  }

  // Check for draw
  if (state.drawReason) {
    const reason = state.drawReason.replace(/_/g, ' ').toLowerCase();
    return { text: `Draw (${reason})`, variant: 'default' };
  }

  // Check winner
  if (state.winner) {
    // Find the current user's player ID from the game
    const userPlayer = game.players?.find(p => p.id === currentUserId);
    const isUserWinner = userPlayer && state.winner === userPlayer.id;

    if (isUserWinner) {
      return { text: 'Won', variant: 'success' };
    } else {
      return { text: 'Lost', variant: 'destructive' };
    }
  }

  // Fallback
  return { text: 'Finished', variant: 'default' };
};

interface ChessGameProps {
  /** If provided, use this game ID instead of reading from route params */
  initialGameId?: string;
  /** If true, this game is embedded in another page (e.g., Agent Run tab) and should not navigate on end */
  isEmbedded?: boolean;
  /** Callback when game is ended (only used when isEmbedded=true) */
  onGameEnded?: () => void;
  /** Callback when reset is requested (only used when isEmbedded=true) */
  onReset?: () => void;
}

export const ChessGame: React.FC<ChessGameProps> = ({ initialGameId, isEmbedded = false, onGameEnded, onReset }) => {
  const { gameId: routeGameId } = useParams<{ gameId?: string }>();
  const navigate = useNavigate();
  const { updateCoinsBalance, user } = useAuth();

  const [game, setGame] = useState<GameStateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [thinking, setThinking] = useState<boolean>(false);
  // Promotion dialog state
  const [promotionOpen, setPromotionOpen] = useState<boolean>(false);
  const [pendingPromotionMove, setPendingPromotionMove] = useState<ChessMoveData | null>(null);
  // End game confirmation dialog state
  const [endGameDialogOpen, setEndGameDialogOpen] = useState<boolean>(false);
  // Event log modal state
  const [eventLogModalOpen, setEventLogModalOpen] = useState<boolean>(false);
  // Tool calls modal state
  const [toolCallsModalOpen, setToolCallsModalOpen] = useState<boolean>(false);
  const [selectedToolCalls, setSelectedToolCalls] = useState<any[]>([]);
  const [selectedAgentName, setSelectedAgentName] = useState<string>("");
  // Victory modal state
  const [victoryModalOpen, setVictoryModalOpen] = useState<boolean>(false);
  const [isVictory, setIsVictory] = useState<boolean>(false);
  const [hasShownVictoryModal, setHasShownVictoryModal] = useState<boolean>(false);

  const [userGames, setUserGames] = useState<GameStateResponse[]>([]);
  const [gamesLoading, setGamesLoading] = useState<boolean>(false);
  const [agentAvatars, setAgentAvatars] = useState<Record<string, { avatarUrl?: string | null; avatarType?: string }>>({});
  const [agentIdsByPlayerId, setAgentIdsByPlayerId] = useState<Record<string, AgentId>>({});
  // Client-side state history for undo/redo and branching
  const { current: histState, reset, push, canRedo, canUndo, undo, redo } = useStateHistory<ChessState>();
  const lastPushedRef = useRef<{ id: GameId | null; v: number }>({ id: null, v: -1 });
  const timeoutFinalizeKeyRef = useRef<string | null>(null);
  const { selectedAgentId, isProfileOpen, showAgentProfile, closeAgentProfile } = useAgentProfile();
  const [activeTab, setActiveTab] = useState<"game" | "info" | "chat" | "events" | "moves" | "board">(() => (isEmbedded ? "chat" : "game"));
  const [unreadChat, setUnreadChat] = useState(0);
  const [unreadEvents, setUnreadEvents] = useState(0);
  const [lastSeenCounts, setLastSeenCounts] = useState({ chat: 0, events: 0 });
  const [playgroundOpponent, setPlaygroundOpponent] = useState<ChessPlaygroundOpponent>('brain');

  // Auto-scroll refs for Reasoning, Moves, and Analysis - separate refs for each breakpoint
  const reasoningScrollRef2xl = useRef<HTMLDivElement>(null);
  const reasoningScrollRefMd = useRef<HTMLDivElement>(null);
  const reasoningScrollRefMobile = useRef<HTMLDivElement>(null);
  const movesScrollRefMd = useRef<HTMLDivElement>(null);
  const movesScrollRef2xl = useRef<HTMLDivElement>(null);

  const movesScrollRefMobile = useRef<HTMLDivElement>(null);
  const analysisScrollRef = useRef<HTMLDivElement>(null);
  const [isReasoningScrolledUp2xl, setIsReasoningScrolledUp2xl] = useState(false);
  const [isReasoningScrolledUpMd, setIsReasoningScrolledUpMd] = useState(false);
  const [isMovesScrolledUp2xl, setIsMovesScrolledUp2xl] = useState(false);

  const [isReasoningScrolledUpMobile, setIsReasoningScrolledUpMobile] = useState(false);
  const [isMovesScrolledUpMd, setIsMovesScrolledUpMd] = useState(false);
  const [isMovesScrolledUpMobile, setIsMovesScrolledUpMobile] = useState(false);
  const lastReasoningCountRef = useRef(0);
  const lastMovesCountRef = useRef(0);

  useEffect(() => {
    if (!game) return;
    const v = (game.version ?? 0);
    if (lastPushedRef.current.id !== game.id) {
      reset(game.state as ChessState);
      lastPushedRef.current = { id: game.id, v };
      return;
    }
    if (lastPushedRef.current.v !== v) {
      push(game.state as ChessState);
      lastPushedRef.current.v = v;
    }
  }, [game?.id, game?.version]);

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

  const ensureBranchIfNeeded = async (): Promise<{ gameId: GameId; state: ChessState }> => {
    const atLatest = !canRedo;
    if (atLatest && game) {
      return { gameId: game.id, state: game.state as ChessState };
    }
    const s = (histState ?? (game?.state as ChessState)) as ChessState;
    const agentId = (game?.players?.[0]?.agentVersionId) ?? (game?.players?.[1]?.agentVersionId);
    const userSide = inferUserSide(game);
    const created = await ChessApiService.createPlaygroundFromState({
      agentId: agentId as AgentVersionId,
      stateView: toStateView(s) as any,
      config: {},
      opponent: playgroundOpponent,
      userSide: playgroundOpponent === 'brain' ? userSide : undefined,
    });
    setGame(created);
    reset(created.state as ChessState);
    setPlaygroundOpponent(inferPlaygroundOpponent(created));
    navigate(`/games/chess/${created.id}`);
    return { gameId: created.id, state: created.state as ChessState };
  };


  const squareToIdx = (square: string): { r: number; c: number } => {
    const file = square.charCodeAt(0) - 97;
    const rank = parseInt(square[1]!, 10);
    return { r: 8 - rank, c: file };
  };
  const needsPromotion = (st: ChessState, move: ChessMoveData): boolean => {
    const { r, c } = squareToIdx(move.fromSquare);
    const piece = st.board[r]?.[c] ?? null;
    if (!piece || piece.type !== 'pawn') return false;
    const targetRank = move.toSquare[1];
    if (!targetRank) return false;
    if (piece.color === 'white') return targetRank === '8';
    return targetRank === '1';
  };

  const usedGameId = initialGameId || routeGameId;

  const loadAgentAvatars = useCallback(async (players: Array<{ agentVersionId?: AgentVersionId; agent_version_id?: AgentVersionId; id: PlayerId }>) => {
    if (!players || players.length === 0) {
      console.debug('[ChessGame] No players to load avatars for');
      return;
    }

    try {
      console.log('[ChessGame] loadAgentAvatars called with players:', JSON.stringify(players, null, 2));

      // Accept both camelCase and snake_case version IDs
      const agentVersionIds = players
        .map((p: any) => {
          const versionId = p.agentVersionId ?? p.agent_version_id;
          console.log(`[ChessGame] Player ${p.id}: agentVersionId=${p.agentVersionId}, agent_version_id=${p.agent_version_id}, resolved=${versionId}`);
          return versionId;
        })
        .filter(Boolean);

      console.debug('[ChessGame] Loading avatars for version IDs:', agentVersionIds);

      if (agentVersionIds.length === 0) {
        console.warn('[ChessGame] No agent version IDs found in players:', players);
        return;
      }

      const avatars = await agentsService.getAgentAvatarsFromVersionIds(agentVersionIds as AgentVersionId[]);
      console.debug('[ChessGame] Loaded avatars:', avatars);

      // Get agent IDs in batch (more efficient than individual calls)
      const agentIdsByVersionId = await agentsService.getAgentIdsFromVersionIdsBatch(agentVersionIds as AgentVersionId[]);
      console.log('[ChessGame] Loaded agent IDs by version:', agentIdsByVersionId);

      // Map avatars and agent IDs by player ID
      const playerAvatars: Record<string, { avatarUrl?: string | null; avatarType?: string }> = {};
      const agentIds: Record<string, AgentId> = {};

      players.forEach((player: any) => {
        const versionId = player.agentVersionId ?? player.agent_version_id;

        // Map avatar
        const avatarInfo = versionId ? avatars[versionId] : undefined;
        if (avatarInfo) {
          playerAvatars[player.id] = avatarInfo;
          // also store under version id to be robust if any consumer uses it
          playerAvatars[String(versionId)] = avatarInfo;
          console.debug(`[ChessGame] Mapped avatar for player ${player.id}:`, avatarInfo);
        } else {
          console.warn(`[ChessGame] No avatar found for player ${player.id} with version ${versionId}`);
        }

        // Map agent ID
        if (versionId) {
          const agentId = agentIdsByVersionId[versionId];
          if (agentId) {
            agentIds[player.id] = agentId;
            console.log(`[ChessGame] Mapped agent ID ${agentId} for player ${player.id}`);
          } else {
            console.warn(`[ChessGame] No agent ID found for player ${player.id} with version ${versionId}`);
          }
        }
      });

      console.log('[ChessGame] Final avatar mapping:', playerAvatars);
      console.log('[ChessGame] Final agent ID mapping:', agentIds);
      console.log('[ChessGame] Players:', players);

      setAgentAvatars(playerAvatars);
      setAgentIdsByPlayerId(agentIds);
    } catch (error) {
      console.error('[ChessGame] Failed to load agent avatars:', error);
    }
  }, []);

  const loadState = useCallback(async () => {
    if (!usedGameId) return;
    setLoading(true);
    try {
      const state = await ChessApiService.getGameState(toGameId(usedGameId));
      setGame(state);
      setPlaygroundOpponent(prev => {
        const inferred = inferPlaygroundOpponent(state);
        return prev === inferred ? prev : inferred;
      });

      // Load agent avatars if we have players
      if (state.players && state.players.length > 0) {
        await loadAgentAvatars(state.players);
      }
    } catch (e) {
      console.error('[ChessGame] Failed to load game state:', e);
      toast.error('Failed to load chess game state');
    } finally {
      setLoading(false);
    }
  }, [usedGameId, loadAgentAvatars]);

  useEffect(() => { if (usedGameId) void loadState(); }, [usedGameId, loadState]);

  // Debug: Log when agentIdsByPlayerId changes
  useEffect(() => {
    console.log('[ChessGame] agentIdsByPlayerId updated:', agentIdsByPlayerId);
    console.log('[ChessGame] game.players:', game?.players);
  }, [agentIdsByPlayerId, game?.players]);

  // Long poll for game state updates during active gameplay
  useEffect(() => {
    if (!usedGameId || !game) return;

    // Don't poll if game is finished
    if (game.state?.isFinished) return;

    let isActive = true;
    let currentVersion = game.version ?? 0;

    const longPoll = async () => {
      while (isActive) {
        try {
          // Long poll with current version - server will wait until version changes
          const updatedState = await ChessApiService.getGameState(
            toGameId(usedGameId),
            currentVersion,  // Use local variable to track version
            30  // 30 second timeout
          );

          if (!isActive) return;

          // Stop polling if game is finished
          if (updatedState.state?.isFinished) {
            isActive = false;
          }

          // Update local version tracker
          currentVersion = updatedState.version ?? 0;
          setGame(updatedState);

          // Load agent avatars if players changed (only on first load)
          if (updatedState.players && updatedState.players.length > 0 && Object.keys(agentAvatars).length === 0) {
            await loadAgentAvatars(updatedState.players);
          }
        } catch (error) {
          // If 404, game doesn't exist - stop polling
          if (error instanceof Error && error.message.includes('404')) {
            isActive = false;
            toast.error('Game no longer exists');
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
  }, [usedGameId, game?.id, game?.state?.isFinished]);

  // Debug: Log agentAvatars state changes
  useEffect(() => {
    console.log('[ChessGame] agentAvatars state updated:', agentAvatars);
    console.log('[ChessGame] agentAvatars keys:', Object.keys(agentAvatars));
    console.log('[ChessGame] Current game players:', game?.players);
  }, [agentAvatars, game?.players]);

  // State for game end reason
  const [gameEndReason, setGameEndReason] = useState<string | undefined>(undefined);

  // Victory modal detection - show modal when game finishes
  useEffect(() => {
    if (!game?.state?.isFinished || !user?.username || hasShownVictoryModal || isEmbedded) return;

    const state = game.state as ChessState;

    // Skip if it's a draw
    if (state.drawReason) {
      return;
    }

    // Find the user's player in the game by username
    const userPlayer = game.players?.find(p => p.username === user.username);

    // Determine if user won
    const didUserWin = userPlayer && state.winner === userPlayer.id;

    // Determine the end reason
    let endReason: string | undefined;
    if (state.forfeitReason) {
      endReason = state.forfeitReason;
    } else if (state.drawReason) {
      endReason = state.drawReason;
    } else {
      // Check events for checkmate or other end conditions
      const gameFinishedEvent = game.events?.find((e: any) => e.type === 'game_finished');
      if (gameFinishedEvent) {
        if ((gameFinishedEvent as any).forfeitReason) {
          endReason = (gameFinishedEvent as any).forfeitReason;
        } else if ((gameFinishedEvent as any).drawReason) {
          endReason = (gameFinishedEvent as any).drawReason;
        }
      }
      // Check for checkmate event
      const checkmateEvent = game.events?.find((e: any) => e.type === 'checkmate');
      if (checkmateEvent) {
        endReason = 'checkmate';
      }
    }

    setGameEndReason(endReason);
    setIsVictory(!!didUserWin);
    setVictoryModalOpen(true);
    setHasShownVictoryModal(true);
  }, [game?.state?.isFinished, game?.state?.winner, game?.state?.drawReason, game?.state?.forfeitReason, game?.events, user?.username, hasShownVictoryModal, isEmbedded, game?.players]);

  useEffect(() => {
    if (usedGameId) return;
    setGamesLoading(true);
    ChessApiService.getUserGames(false)
      .then(setUserGames)
      .catch(() => toast.error('Failed to load your chess games'))
      .finally(() => setGamesLoading(false));
  }, [usedGameId]);

  useEffect(() => {
    const evs = (game?.events ?? []) as any[];
    const chatCount = evs.filter((e: any) => e?.type === "chat_message").length;
    const eventCount = evs.filter((e: any) => e?.type !== "chat_message").length;

    // If Info tab is open, consider both chat and events as read
    const chatOpen = activeTab === "chat" || activeTab === "info";
    const eventsOpen = activeTab === "events" || activeTab === "info";

    if (!chatOpen) {
      setUnreadChat(Math.max(0, chatCount - lastSeenCounts.chat));
    } else {
      setUnreadChat(0);
      setLastSeenCounts((prev) => ({ ...prev, chat: chatCount }));
    }

    if (!eventsOpen) {
      setUnreadEvents(Math.max(0, eventCount - lastSeenCounts.events));
    } else {
      setUnreadEvents(0);
      setLastSeenCounts((prev) => ({ ...prev, events: eventCount }));
    }
  }, [game?.events, activeTab]);

  // Initial scroll-to-bottom for all panels when component mounts (parity with Playground)
  useEffect(() => {
    const els = [
      reasoningScrollRef2xl.current,
      reasoningScrollRefMd.current,
      reasoningScrollRefMobile.current,
      movesScrollRef2xl.current,
      movesScrollRefMd.current,
      movesScrollRefMobile.current,
      analysisScrollRef.current,
    ].filter(Boolean) as HTMLDivElement[];
    els.forEach((el) => {
      el.scrollTop = el.scrollHeight;
    });
  }, []);

  // Auto-scroll setup for Reasoning 2xl
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

  // Auto-scroll setup for Reasoning Md
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

  // Auto-scroll setup for Reasoning Mobile
  useEffect(() => {
    if (!reasoningScrollRefMobile.current) return;
    const handleScroll = () => {
      const el = reasoningScrollRefMobile.current;
      if (!el) return;
      const { scrollTop, scrollHeight, clientHeight } = el;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50;
      setIsReasoningScrolledUpMobile(!isAtBottom);
    };
    const el = reasoningScrollRefMobile.current;
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  // Auto-scroll setup for Moves Md
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

  // Auto-scroll setup for Moves Mobile
  useEffect(() => {
    if (!movesScrollRefMobile.current) return;
    const handleScroll = () => {
      const el = movesScrollRefMobile.current;
      if (!el) return;
      const { scrollTop, scrollHeight, clientHeight } = el;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50;
      setIsMovesScrolledUpMobile(!isAtBottom);
    };
    const el = movesScrollRefMobile.current;
    el.addEventListener('scroll', handleScroll);

    return () => el.removeEventListener('scroll', handleScroll);
  }, []);



  // Derive white/black player IDs from game players
  const players = useMemo<[PlayerId, PlayerId] | null>(() => {
    if (!game?.players || game.players.length !== 2) {
      return null;
    }

    const st = game?.state as ChessState | undefined;
    if (!st) {
      return null;
    }

    // For chess, we need to determine which player is white and which is black
    // We can use the game.players array which should be ordered correctly
    const playerIds = game.players.map(p => p.id) as [PlayerId, PlayerId];

    // If we have remainingTimeMs data, use it to determine the order
    const timeKeys = Object.keys(st.remainingTimeMs || {}) as PlayerId[];
    if (timeKeys.length === 2) {
      const other = (pid: PlayerId) => (timeKeys[0] === pid ? timeKeys[1] : timeKeys[0]);
      if (st.sideToMove === 'white') {
        return [st.currentPlayerId, other(st.currentPlayerId)];
      }
      return [other(st.currentPlayerId), st.currentPlayerId];
    }

    // Fallback: assume first player is white, second is black
    return playerIds;
  }, [game]);

  const handleMoveSelected = async (move: ChessMoveData) => {
    // Ensure we are acting on the correct timeline: if user is at a past state, branch a new playground
    const { gameId, state } = await ensureBranchIfNeeded();
    const st = state as any; // tolerate camelCase variants

    // If promotion is needed and not provided, open dialog to choose piece
    if (!move.promotion && needsPromotion(st, move)) {
      setPendingPromotionMove(move);
      setPromotionOpen(true);
      return;
    }

    const cur = st.currentPlayerId;
    const turn = st.turn || 0;
    console.debug('[ChessGame] submit move', { gameId, playerId: cur, move, turn });
    try {
      const res: TurnResultResponse = await ChessApiService.executeTurn(gameId, cur, move, turn);
      console.debug('[ChessGame] move result', { newState: res.newState, newEvents: res.newEvents });
      setGame((prev) => prev && prev.id === gameId
        ? { ...prev, state: res.newState, events: [...prev.events, ...(res.newEvents ?? [])], version: (prev.version ?? 0) + 1 }
        : prev);
      // Update coins balance immediately from response
      if (res.newCoinsBalance !== undefined && res.newCoinsBalance !== null) {
        updateCoinsBalance(res.newCoinsBalance);
      }
    } catch (e) {
      console.error('[ChessGame] move error', e);
      const msg = e instanceof Error && e.message ? e.message : 'Move rejected by server';
      // If backend requires promotion piece, show dialog to complete the move
      if (msg.includes('Promotion piece required') && pendingPromotionMove == null) {
        setPendingPromotionMove(move);
        setPromotionOpen(true);
        return;
      }
      // Friendlier message for illegal moves (common when in check)
      if (msg.includes('Illegal move')) {
        toast.warning('Illegal move. If you are in check, choose a move that blocks, captures, or moves the king.');
        return;
      }
      toast.error(msg);
    }
  };

  const handleEndGame = async () => {
    if (!game?.id) return;

    try {
      // If embedded (e.g., in Agent Run tab), let the parent handle deletion
      if (isEmbedded && onGameEnded) {
        toast.success('Game ended successfully');
        onGameEnded();
      } else {
        // Otherwise, delete the game and navigate to the games list
        await ChessApiService.deleteGame(game.id);
        toast.success('Game ended successfully');
        navigate('/games/chess');
      }
    } catch (e) {
      console.error(e);
      toast.error('Failed to end game');
    } finally {
      setEndGameDialogOpen(false);
    }
  };

  const stateView = (game?.state as unknown as ChessStateView) || null;
  const currentPlayerId = (game?.state as ChessState)?.currentPlayerId;


  // Proactive timeout UX: compute local time expiry for the active side
  // Only update timer when game is active and not finished
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  useEffect(() => {
    const st = game?.state as ChessState | undefined;
    // Only run timer if game is active and not finished
    if (!st || st.isFinished || game?.isPlayground) {
      return;
    }

    // Update every 1 second instead of 200ms to reduce re-renders
    const id = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [game?.state?.isFinished, game?.isPlayground]);

  useEffect(() => {
    setPlaygroundOpponent(prev => {
      const inferred = inferPlaygroundOpponent(game);
      return prev === inferred ? prev : inferred;
    });
  }, [game]);

  const timeoutPending = useMemo(() => {
    const st = game?.state as ChessState | undefined;
    if (!st || st.isFinished) return false;

    // Never show timeout in playground mode
    if (game?.isPlayground) return false;

    // Check if timers are disabled (e.g., in playground mode)
    const config = game?.config as { disable_timers?: boolean } | undefined;
    if (config?.disable_timers) return false;

    const lastTs = st.lastTimestampMs ?? null;
    if (lastTs == null) return false;
    const base = (st.remainingTimeMs || {})[st.currentPlayerId] ?? 0;
    const elapsed = Math.max(0, nowMs - lastTs);
    return (base - elapsed) <= 0;
  }, [game?.state, game?.config, game?.isPlayground, nowMs]);

  useEffect(() => {
    if (!timeoutPending || !game?.id || !currentPlayerId) {
      if (!timeoutPending) {
        timeoutFinalizeKeyRef.current = null;
      }
      return;
    }

    const attemptKey = `${game.id}:${game.version ?? 0}`;
    if (timeoutFinalizeKeyRef.current === attemptKey) {
      return;
    }

    timeoutFinalizeKeyRef.current = attemptKey;
    let cancelled = false;

    (async () => {
      try {
        const result = await ChessApiService.finalizeTimeout(game.id, currentPlayerId);
        if (cancelled) return;

        setGame((prev) => {
          if (!prev || prev.id !== result.gameId) {
            return prev;
          }

          const priorEvents = prev.events ?? [];
          const nextEvents = result.newEvents && result.newEvents.length > 0
            ? [...priorEvents, ...result.newEvents]
            : priorEvents;

          return {
            ...prev,
            state: result.newState as ChessState,
            events: nextEvents,
            version: (prev.version ?? 0) + 1,
            matchmakingStatus: result.isFinished ? "finished" : (prev.matchmakingStatus ?? null),
          };
        });
      } catch (error) {
        console.warn("[ChessGame] Failed to finalize timeout:", error);
        timeoutFinalizeKeyRef.current = null;
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [timeoutPending, game?.id, game?.version, currentPlayerId]);

  // Resolve white/black names based on computed players mapping
  const whitePlayerName = useMemo(() => {
    if (!game?.players || !players) return undefined;
    const whiteId = players[0];
    const player = game.players.find((p: any) => p.id === whiteId);
    if (!player) return 'White';
  const agentName = player.name || 'White';
  const display = (player as any).displayName ?? player.username;
  return display ? `${agentName} (${display})` : agentName;
  }, [game?.players, players]);
  const blackPlayerName = useMemo(() => {
    if (!game?.players || !players) return undefined;
    const blackId = players[1];
    const player = game.players.find((p: any) => p.id === blackId);
    if (!player) return 'Black';
  const agentName = player.name || 'Black';
  const display = (player as any).displayName ?? player.username;
  return display ? `${agentName} (${display})` : agentName;
  }, [game?.players, players]);

  const whiteRating = useMemo(() => {
    if (!game?.players || !players) return undefined;
    const whiteId = players[0];
    return game.players.find((p: any) => p.id === whiteId)?.rating;
  }, [game?.players, players]);

  const blackRating = useMemo(() => {
    if (!game?.players || !players) return undefined;
    const blackId = players[1];
    return game.players.find((p: any) => p.id === blackId)?.rating;
  }, [game?.players, players]);

  // Determine user's color for board orientation
  const userColor = useMemo((): ChessSide => {
    if (!game) return 'white';

    // For playground games, use inferUserSide from config
    if (game.isPlayground) {
      return inferUserSide(game);
    }

    // For real games, determine which player belongs to the current user
    // Use the color field from player data which is set by the backend
    if (user && game.players && game.players.length === 2) {
      // Find the player that belongs to the current user by username
      const userPlayer = game.players.find(p => p.username === user.username);
      if (userPlayer?.color) {
        return userPlayer.color;
      }
    }

    // Fallback: check config for userSide
    const configSide = (game.config as Record<string, any> | undefined | null)?.userSide
      ?? (game.config as Record<string, any> | undefined | null)?.user_side;
    if (configSide === 'white' || configSide === 'black') {
      return configSide;
    }

    // Default to white if we can't determine
    return 'white';
  }, [game, user]);

  // Extract move and reasoning events for sidebar cards
  const moveEvents = useMemo(() => {
    const evs = (game?.events || []) as any[];
    return evs.filter((e: any) => (e.type || e.eventType) === 'move_played').map((e: any, idx: number) => {
      const from = e.fromSquare ?? e.from_square ?? e.move?.fromSquare ?? e.move?.from;
      const to = e.toSquare ?? e.to_square ?? e.move?.toSquare ?? e.move?.to;
      const san = e.move?.san || e.san;
      return { id: e.id || `mv-${idx}`, text: san ? san : (from && to ? `${from} 2 ${to}` : 'Move') };
    });
  }, [game?.events]);

  // All reasoning events for scrollable list
  const reasoningEvents = useMemo(() => {
    const evs = (game?.events || []) as any[];
    const filtered = evs
      .filter((e: any) => e?.type === "agent_reasoning" || e?.type === "agent_forfeit")
      .map((e: any) => {
        const isForfeit = e?.type === "agent_forfeit";
        return {
          id: e.id || `reasoning-${e.timestamp}`,
          playerId: e.player_id || e.playerId,
          reasoning: isForfeit
            ? `FORFEIT: ${e.reason || "Failed to move within attempt limit"}`
            : (e.reasoning || ""),
          timestamp: e.timestamp,
          // Backend sends toolCalls (camelCase), but also check tool_calls (snake_case) for compatibility
          toolCalls: e.toolCalls || e.tool_calls || [],
          isForfeit,
        };
      });

    return filtered;
  }, [game?.events]);
  // Get all analysis events (not just the last one)
  const allAnalyses = useMemo(() => {
    const evs = (game?.events || []) as any[];
    return evs
      .filter((e: any) => {
        const t = e?.type || e?.eventType;
        return t === 'move_analysis';
      })
      .map((e: any) => ({
        moveSan: e.moveSan || e.move_san,
        narrative: e.narrative,
        bestMoveSan: e.bestMoveSan || e.best_move_san,
        evaluationCp: e.evaluationCp ?? e.evaluation_cp,
        evaluationMate: e.evaluationMate ?? e.evaluation_mate,
        isBrilliant: e.isBrilliant ?? e.is_brilliant ?? false,
        isGood: e.isGood ?? e.is_good ?? false,
        isInaccuracy: e.isInaccuracy ?? e.is_inaccuracy ?? false,
        isMistake: e.isMistake ?? e.is_mistake ?? false,
        isBlunder: e.isBlunder ?? e.is_blunder ?? false,
        roundNumber: e.roundNumber ?? e.round_number,
        timestamp: e.timestamp,
      }));
  }, [game?.events]);

  // Auto-scroll Reasoning when new items arrive - handle all refs
  useEffect(() => {
    const hasNewItems = reasoningEvents.length > lastReasoningCountRef.current;
    lastReasoningCountRef.current = reasoningEvents.length;

    if (hasNewItems) {
      // Scroll 2xl reasoning if not scrolled up
      if (!isReasoningScrolledUp2xl && reasoningScrollRef2xl.current) {
        reasoningScrollRef2xl.current.scrollTop = reasoningScrollRef2xl.current.scrollHeight;
      }
      // Scroll md reasoning if not scrolled up
      if (!isReasoningScrolledUpMd && reasoningScrollRefMd.current) {
        reasoningScrollRefMd.current.scrollTop = reasoningScrollRefMd.current.scrollHeight;
      }
      // Scroll mobile reasoning if not scrolled up
      if (!isReasoningScrolledUpMobile && reasoningScrollRefMobile.current) {
        reasoningScrollRefMobile.current.scrollTop = reasoningScrollRefMobile.current.scrollHeight;
      }
    }
  }, [reasoningEvents, isReasoningScrolledUp2xl, isReasoningScrolledUpMd, isReasoningScrolledUpMobile]);

  // Auto-scroll Moves when new items arrive - handle all refs
  useEffect(() => {
    const hasNewItems = moveEvents.length > lastMovesCountRef.current;
    lastMovesCountRef.current = moveEvents.length;

    if (hasNewItems) {
      // Scroll 2xl moves if not scrolled up
      if (!isMovesScrolledUp2xl && movesScrollRef2xl.current) {
        movesScrollRef2xl.current.scrollTop = movesScrollRef2xl.current.scrollHeight;
      }
      // Scroll md moves if not scrolled up
      if (!isMovesScrolledUpMd && movesScrollRefMd.current) {
        movesScrollRefMd.current.scrollTop = movesScrollRefMd.current.scrollHeight;
      }
      // Scroll mobile moves if not scrolled up
      if (!isMovesScrolledUpMobile && movesScrollRefMobile.current) {
        movesScrollRefMobile.current.scrollTop = movesScrollRefMobile.current.scrollHeight;
      }
    }
  }, [moveEvents, isMovesScrolledUp2xl, isMovesScrolledUpMd, isMovesScrolledUpMobile]);

  // Auto-scroll Analysis when new items arrive
  useEffect(() => {
    if (analysisScrollRef.current) {
      analysisScrollRef.current.scrollTop = analysisScrollRef.current.scrollHeight;
    }
  }, [allAnalyses]);

  const lastMove = useMemo(() => {
    const evs = (game?.events as any[] | undefined) ?? [];
    for (let i = evs.length - 1; i >= 0; i--) {
      const ev = evs[i];
      if (!ev) continue;
      const type = ev.type || ev.eventType;
      if (type === 'move_played') {

        const from = ev.fromSquare ?? ev.from_square ?? ev.move?.fromSquare ?? ev.move?.from;
        const to = ev.toSquare ?? ev.to_square ?? ev.move?.toSquare ?? ev.move?.to;
        if (typeof from === 'string' && typeof to === 'string') {
          return { from, to } as const;
        }
      }
    }
    return null;
  }, [game?.events]);

  // Render the snapshot from history if present; else live state
  const renderState: ChessStateView = (histState ?? (game?.state as unknown as ChessState)) as unknown as ChessStateView;
  const atLatest = !canRedo;

  return (
    <div
      className={
        isEmbedded
          ? "w-full h-full min-h-0 flex flex-col px-0"
          : "container mx-auto max-w-screen-2xl px-4 pt-3 pb-3 md:pt-2 md:pb-2 h-full flex flex-col"
      }>




	      {timeoutPending && (
	        <div className="mb-3 rounded-md bg-rose-50 dark:bg-rose-900/20 p-3 text-sm">
	          Time expired for the side to move. Waiting for server to finalize the result…
	        </div>
	      )}

      {game && stateView && players && currentPlayerId ? (
        <div className={`grid min-w-0 grid-cols-1 flex-1 min-h-0 ${isEmbedded
          ? 'md:grid-cols-[minmax(0,1fr)_320px] lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[280px_minmax(0,1fr)_340px] md:overflow-hidden'
          : 'md:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[280px_minmax(0,1fr)_360px] md:overflow-hidden'
        } gap-3`}>
            {/* Left: Game Analysis and Moves (2xl screens only) */}
            <div className="hidden 2xl:flex 2xl:min-w-0 2xl:flex-col 2xl:gap-3 2xl:h-full 2xl:overflow-hidden pt-1">
              <AnalysisCard
                analyses={allAnalyses}
                scrollRef={analysisScrollRef}
                className="flex flex-col overflow-hidden 2xl:flex-1 2xl:min-h-0"
              />
              <MovesCard
                moves={moveEvents}
                scrollRef={movesScrollRef2xl}
                className="flex-shrink-0 h-[12vh] flex flex-col overflow-hidden"
                testId="moves-card-2xl"
              />
            </div>

          {/* Middle: Controls, Board, and Game Analysis */}
          <div className={`${isEmbedded ? 'flex' : 'hidden md:flex'} flex-col min-w-0 space-y-2 md:h-full md:overflow-hidden pt-1`}>
            {/* Controls Card - at the top */}
            <Card className="flex-shrink-0 bg-amber-50/30 dark:bg-card">
              <CardHeader className="py-1">
                <CardTitle className="text-center text-xs md:text-sm">
                  <Crown className="inline-block w-5 h-5 md:w-6 md:h-6 text-yellow-500" aria-label="Chess" />
                  <span className="ml-2 align-middle text-[10px] px-1.5 py-0.5 rounded bg-brand-mint/15 text-brand-mint">ChessGame</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 p-2 md:p-3">
                <div className="flex items-center justify-center gap-2 flex-wrap">
                  {game?.isPlayground && (
                    <>
                      <Button size="sm" variant="outline" onClick={async () => {
                        if (!game) return;
                        if (isEmbedded && onReset) { onReset(); return; }
                        try {
                          const agentId = game.players?.[0]?.agentVersionId ?? game.players?.[1]?.agentVersionId;
                          const userSide = inferUserSide(game);
                          const created = await ChessApiService.createPlaygroundFromState({
                            agentId: agentId as AgentVersionId,
                            stateView: {},
                            config: {},
                            opponent: playgroundOpponent,
                            userSide: playgroundOpponent === 'brain' ? userSide : undefined,
                          });
                          setGame(created);
                          reset(created.state as ChessState);
                          setPlaygroundOpponent(prev => {
                            const inferred = inferPlaygroundOpponent(created);
                            return prev === inferred ? prev : inferred;
                          });
                        } catch (e) {
                          const msg = e instanceof Error && e.message ? e.message : 'Reset failed';
                          toast.error(msg);
                        }
                      }} disabled={!game}>Reset</Button>
                      <Button size="sm" variant="outline" disabled={loading} onClick={() => void loadState()}>Refresh</Button>
                      {/* Time travel controls */}
                      <Button size="sm" variant="outline" onClick={() => canUndo && undo()} disabled={!canUndo}>Back</Button>
                      <Button size="sm" variant="outline" onClick={() => canRedo && redo()} disabled={!canRedo}>Forward</Button>
                      <span className="text-[11px] text-muted-foreground hidden md:inline-block ml-2">
                        {canRedo ? 'Viewing past' : 'Live'}
                      </span>
                      <Button size="sm" variant="destructive" onClick={() => setEndGameDialogOpen(true)}>
                        End Game
                      </Button>
                      <Button size="sm" disabled={thinking || renderState.isFinished || !atLatest} className="bg-brand-orange text-white hover:bg-brand-orange/90" onClick={async () => {
                        setThinking(true);
                        try {
                          const { gameId, state } = await ensureBranchIfNeeded();
                          const cur = (state as ChessState).currentPlayerId;
                          const turn = (state as ChessState).turn || 0;
                          const res = await ChessApiService.executeTurn(gameId, cur, null, turn);
                          setGame((prev) => prev && prev.id === gameId ? { ...prev, state: res.newState, events: [...prev.events, ...(res.newEvents ?? [])], version: (prev.version ?? 0) + 1 } : prev);
                          // Update coins balance immediately from response
                          if (res.newCoinsBalance !== undefined && res.newCoinsBalance !== null) {
                            updateCoinsBalance(res.newCoinsBalance);
                          }
                        } catch (e) {
                          console.error(e);
                          const msg = e instanceof Error && e.message ? e.message : 'Agent turn failed';
                          toast.error(msg);
                        } finally {
                          setThinking(false);
                        }
                      }}>
                        {thinking ? 'Thinking…' : 'Let agent play'}
                      </Button>
                    </>
                  )}

                  {/* TEMPORARY: Agent play button for real games when flag is enabled */}
                  {SHOW_AGENT_PLAY_IN_REAL_GAMES && !game?.isPlayground && (
                    <Button size="sm" disabled={thinking || renderState.isFinished || !atLatest} className="bg-brand-orange text-white hover:bg-brand-orange/90" onClick={async () => {
                      setThinking(true);
                      try {
                        const { gameId, state } = await ensureBranchIfNeeded();
                        const cur = (state as ChessState).currentPlayerId;
                        const turn = (state as ChessState).turn || 0;
                        const res = await ChessApiService.executeTurn(gameId, cur, null, turn);
                        setGame((prev) => prev && prev.id === gameId ? { ...prev, state: res.newState, events: [...prev.events, ...(res.newEvents ?? [])], version: (prev.version ?? 0) + 1 } : prev);
                        // Update coins balance immediately from response
                        if (res.newCoinsBalance !== undefined && res.newCoinsBalance !== null) {
                          updateCoinsBalance(res.newCoinsBalance);
                        }
                      } catch (e) {
                        console.error(e);
                        const msg = e instanceof Error && e.message ? e.message : 'Agent turn failed';
                        toast.error(msg);
                      } finally {
                        setThinking(false);
                      }
                    }}>
                      {thinking ? 'Thinking…' : 'Let agent play'}
                    </Button>
                  )}

                  {/* View Event Log button - always visible */}
                  <Button size="sm" variant="outline" onClick={() => setEventLogModalOpen(true)}>
                    View Event Log
                  </Button>
                </div>
                {/* Mobile: chip centered + clocks below */}
                <div className="md:hidden flex justify-center">
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
                {!game?.isPlayground && stateView && (
                  <div className="md:hidden mt-1 flex justify-center">
                    <ChessClocks state={stateView} players={players} currentPlayerId={currentPlayerId} />
                  </div>
                )}

                {/* Desktop: clocks on sides, chip centered */}
                <div className="hidden md:grid grid-cols-[auto,1fr,auto] items-center">
                  {(!game?.isPlayground && stateView) ? (
                    <ChessClocks className="justify-self-start" state={stateView} players={players!} currentPlayerId={currentPlayerId!} render="white" />
                  ) : (
                    <div />
                  )}
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
                  {(!game?.isPlayground && stateView) ? (
                    <ChessClocks className="justify-self-end" state={stateView} players={players!} currentPlayerId={currentPlayerId!} render="black" />
                  ) : (
                    <div />
                  )}
                </div>

                {renderState.isFinished && (
                  <div className="rounded-md bg-amber-50 dark:bg-amber-900/20 p-3 text-sm flex items-center justify-between">
                    <span>Game finished. {game?.isPlayground ? 'Create another playground to play again.' : 'Start a new game to play again.'}</span>
                    {!game?.isPlayground && (
                      <Button size="sm" onClick={() => navigate('/games')}>Start new game</Button>

                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Board Card - below controls */}
            <Card className="flex-1 min-h-0 overflow-hidden bg-amber-50/30 dark:bg-card">
              <CardContent className="p-0 h-full flex items-center justify-center">
                <ChessBoard
                  state={renderState}
                  onMoveSelected={(game?.isPlayground && !renderState.isFinished && !timeoutPending) ? handleMoveSelected : undefined}
                  lastMove={atLatest ? lastMove : null}
                  hideCapturedPieces={isEmbedded}
                  whitePlayerName={whitePlayerName}
                  blackPlayerName={blackPlayerName}
                  whiteRating={whiteRating}
                  blackRating={blackRating}
                  whitePlayerAvatar={players ? agentAvatars[players[0]] : undefined}
                  blackPlayerAvatar={players ? agentAvatars[players[1]] : undefined}
                  onWhitePlayerClick={players ? () => {
                    console.log('[ChessGame] White player clicked');
                    console.log('[ChessGame] players:', players);
                    console.log('[ChessGame] agentIdsByPlayerId:', agentIdsByPlayerId);
                    console.log('[ChessGame] players[0]:', players[0]);
                    console.log('[ChessGame] agentIdsByPlayerId[players[0]]:', agentIdsByPlayerId[players[0]]);
                    const agentId = agentIdsByPlayerId[players[0]];
                    if (agentId) {
                      showAgentProfile(agentId);
                    } else {
                      console.error('[ChessGame] No agentId found for white player:', players[0]);
                    }
                  } : undefined}
                  onBlackPlayerClick={players ? () => {
                    console.log('[ChessGame] Black player clicked');
                    console.log('[ChessGame] players:', players);
                    console.log('[ChessGame] agentIdsByPlayerId:', agentIdsByPlayerId);
                    console.log('[ChessGame] players[1]:', players[1]);
                    console.log('[ChessGame] agentIdsByPlayerId[players[1]]:', agentIdsByPlayerId[players[1]]);
                    const agentId = agentIdsByPlayerId[players[1]];
                    if (agentId) {
                      showAgentProfile(agentId);
                    } else {
                      console.error('[ChessGame] No agentId found for black player:', players[1]);
                    }
                  } : undefined}
                  flipped={userColor === 'black'}
                />
              </CardContent>
            </Card>


            {/* Mobile-only Reasoning when embedded in AgentRunTab Game view */}
            {isEmbedded && (
              <Card className="md:hidden flex-shrink-0 flex flex-col h-[260px] overflow-hidden">
                <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
                  <CardTitle className="text-lg flex items-center gap-2"><Brain className="w-5 h-5 text-brand-mint" /> Reasoning</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pb-4">
                  {reasoningEvents.length > 0 ? (
                    <div className="space-y-3">
                      {reasoningEvents.map((r) => (
                        <div key={r.id} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                          <div className="flex items-center gap-2">
                            <Avatar
                              src={agentAvatars[r.playerId]?.avatarUrl}
                              fallback={game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent"}
                              size="sm"
                              className="flex-shrink-0"
                            />
                            <div className="font-medium text-brand-teal text-xs">{game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent"}</div>
                          </div>
                          <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{r.reasoning}</div>
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
                    <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No reasoning yet</div>
                  )}
                </CardContent>
              </Card>
            )}


          </div>

          {/* Promotion dialog */}
          <Dialog open={promotionOpen} onOpenChange={setPromotionOpen}>
            <DialogContent className="md:min-w-[400px]">
              <DialogHeader>
                <DialogTitle>Choose promotion piece</DialogTitle>
                <DialogDescription>Select the piece to promote your pawn to.</DialogDescription>
              </DialogHeader>

              <DialogFooter>
                {(['q','r','b','n'] as const).map((p) => {
                  const pieceType = p === 'q' ? 'queen' : p === 'r' ? 'rook' : p === 'b' ? 'bishop' : 'knight';
                  return (
                    <Button
                      key={p}
                      size="sm"
                      aria-label={`Promote to ${pieceType}`}
                      onClick={async () => {
                        if (!game?.id || !pendingPromotionMove) { setPromotionOpen(false); return; }
                        const st = game.state as ChessState;
                        const cur = st.currentPlayerId;
                        const move = { ...pendingPromotionMove, promotion: p } as ChessMoveData;
                        try {
                          const turn = (game.state as ChessState).turn || 0;
                          const res = await ChessApiService.executeTurn(game.id, cur, move, turn);
                          setGame({ ...game, state: res.newState, events: [...game.events, ...(res.newEvents ?? [])], version: (game.version ?? 0) + 1 });
                        } catch (e) {
                          const msg = e instanceof Error && e.message ? e.message : 'Promotion failed';
                          toast.error(msg);
                        } finally {
                          setPromotionOpen(false);
                          setPendingPromotionMove(null);
                        }
                      }}
                    >
                      <ChessPieceView piece={{ type: pieceType as any, color: stateView.sideToMove }} />
                    </Button>
                  );
                })}
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* End Game Confirmation Dialog */}
          <Dialog open={endGameDialogOpen} onOpenChange={setEndGameDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>End Game?</DialogTitle>
                <DialogDescription>
                  Are you sure you want to end this game? This will delete the game from the database and cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEndGameDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={handleEndGame}>
                  End Game
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Event Log Modal via SharedModal */}
          <SharedModal open={eventLogModalOpen} onOpenChange={setEventLogModalOpen} title="Event Log" size="xl">
            <div className="flex-1 max-h-[70vh] overflow-auto">
              <EventLog events={(game.events || []) as any} maxHeight="60vh" noMargin noCard />
            </div>
          </SharedModal>

          {/* Right: Sidebar (fixed 360px on desktop, full width on mobile) */}
          <div className="flex flex-col min-w-0 gap-3 md:h-full md:min-h-0 md:overflow-hidden pt-1">
            {game.isPlayground ? (
              <>
                {/* Desktop: Moves, Chat, Reasoning, and Analysis */}
                <div className="hidden md:flex md:flex-col md:gap-3 md:h-full md:overflow-hidden md:pt-0">
                  <MovesCard
                    moves={moveEvents}
                    scrollRef={movesScrollRefMd}
                    className="flex-shrink-0 h-[14vh] flex flex-col overflow-hidden"
                  />

                  {/* Chat Window - hidden on 2xl+ (shown in left column), small fixed height */}
                  <Card className="flex-shrink-0 h-[18vh] flex flex-col overflow-hidden bg-violet-50/50 dark:bg-card">
                    <ChatWindow
                      messages={(game.events || [])
                        .filter((e: any) => e.type === 'chat_message')
                        .map((e: any) => ({
                          playerId: e.player_id || e.playerId,
                          message: e.message,
                          timestamp: e.timestamp,
                        }))}
                      playerNames={game.players?.reduce((acc: Record<string, string>, p: any) => {
                        acc[p.id] = p.name || `Player ${p.id.slice(0, 8)}`;
                        return acc;
                      }, {}) || {}}
                      playerAvatars={agentAvatars}
                      onPlayerClick={(playerId) => {
                        console.log('[ChessGame] Chat player clicked, playerId:', playerId, 'agentIdsByPlayerId:', agentIdsByPlayerId);
                        const agentId = agentIdsByPlayerId[playerId];
                        console.log('[ChessGame] Found agentId:', agentId);
                        if (agentId) {
                          showAgentProfile(agentId);
                        } else {
                          console.warn('[ChessGame] No agentId found for playerId:', playerId);
                        }
                      }}
                    />
                  </Card>

                  <ReasoningCard
                    reasoningEvents={reasoningEvents}
                    playerInfo={Object.fromEntries(
                      (game.players || []).map((p: any) => [
                        p.id,
                        {
                          name: p.name || `Player ${p.id.slice(0, 8)}`,
                          avatarUrl: agentAvatars[p.id]?.avatarUrl,
                          avatarType: agentAvatars[p.id]?.avatarType,
                        },
                      ])
                    )}
                    onShowAgentProfile={(playerId) => {
                      console.log('[ChessGame] Reasoning player clicked, playerId:', playerId, 'agentIdsByPlayerId:', agentIdsByPlayerId);
                      const agentId = agentIdsByPlayerId[playerId];
                      console.log('[ChessGame] Found agentId:', agentId);
                      if (agentId) {
                        showAgentProfile(agentId);
                      } else {
                        console.warn('[ChessGame] No agentId found for playerId:', playerId);
                      }
                    }}
                    onShowToolCalls={(toolCalls) => {
                      setSelectedToolCalls(toolCalls);
                      setToolCallsModalOpen(true);
                    }}
                    scrollRef={reasoningScrollRefMd}
                    className="2xl:hidden flex-shrink-0 h-[28vh] flex flex-col overflow-hidden"
                    testId="reasoning-card"
                  />

                  <AnalysisCard
                    analyses={allAnalyses}
                    scrollRef={analysisScrollRef}
                    className="2xl:hidden flex-1 min-h-0 flex flex-col overflow-hidden"
                    testId="analysis-card-md"
                  />
                </div>

                {/* Mobile: Game/Info tabs matching real game pattern */}
                {!isEmbedded && (
                <Card className="md:hidden">
                  <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v as any); const evs = (game?.events ?? []) as any[]; const chatCount = evs.filter((e: any) => e?.type === 'chat_message').length; const eventCount = evs.filter((e: any) => e?.type !== 'chat_message').length; if (v === 'info') { setLastSeenCounts({ chat: chatCount, events: eventCount }); } }} className="w-full">
                    <CardHeader className="pb-3">
                      <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="game" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                          <Crown className="w-4 h-4 mr-2" />
                          Game
                        </TabsTrigger>
                        <TabsTrigger value="info" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                          <Settings className="w-4 h-4 mr-2" />
                          Info
                          {(unreadChat + unreadEvents) > 0 && (
                            <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-orange px-1 text-[10px] text-white">
                              {unreadChat + unreadEvents}
                            </span>
                          )}
                        </TabsTrigger>
                      </TabsList>
                    </CardHeader>
                    <CardContent className="p-0">
                      {/* Game tab: show the board */}
                      <TabsContent value="game" className="mt-0">
                        <div className="px-2 py-4 space-y-3">
                          {/* Board */}
                          <div className="flex items-center justify-center">
                            <ChessBoard
                              state={renderState}
                              onMoveSelected={(game?.isPlayground && !renderState.isFinished && !timeoutPending) ? handleMoveSelected : undefined}
                              lastMove={atLatest ? lastMove : null}
                              hideCapturedPieces={isEmbedded}
                              whitePlayerName={whitePlayerName}
                              blackPlayerName={blackPlayerName}
                              whiteRating={whiteRating}
                              blackRating={blackRating}
                              whitePlayerAvatar={players ? agentAvatars[players[0]] : undefined}
                              blackPlayerAvatar={players ? agentAvatars[players[1]] : undefined}
                              onWhitePlayerClick={players ? () => {
                                console.log('[ChessGame Mobile] White player clicked, players[0]:', players[0], 'agentId:', agentIdsByPlayerId[players[0]]);
                                const agentId = agentIdsByPlayerId[players[0]];
                                if (agentId) showAgentProfile(agentId);
                                else console.error('[ChessGame Mobile] No agentId for white player');
                              } : undefined}
                              onBlackPlayerClick={players ? () => {
                                console.log('[ChessGame Mobile] Black player clicked, players[1]:', players[1], 'agentId:', agentIdsByPlayerId[players[1]]);
                                const agentId = agentIdsByPlayerId[players[1]];
                                if (agentId) showAgentProfile(agentId);
                                else console.error('[ChessGame Mobile] No agentId for black player');
                              } : undefined}
                              flipped={userColor === 'black'}
                            />
                          </div>
                        </div>
                      </TabsContent>

                      {/* Info tab: Moves, Reasoning, Analysis, Chat */}
                      <TabsContent value="info" className="mt-0">
                        <div className="space-y-3 px-2 pb-4">
                          {/* Moves */}
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center gap-2">
                                <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0 max-h-[220px] overflow-y-auto" ref={movesScrollRefMobile}>
                              {moveEvents.length === 0 ? (
                                <div className="text-xs text-muted-foreground">No moves yet.</div>
                              ) : (
                                <ol className="text-sm space-y-1 pl-4 list-decimal">
                                  {moveEvents.map((m) => (
                                    <li key={m.id} className="leading-snug">{m.text}</li>
                                  ))}
                                </ol>
                              )}
                            </CardContent>
                          </Card>

                          {/* Reasoning */}
                          <Card className="flex flex-col h-[320px] overflow-hidden">
                            <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
                              <CardTitle className="text-base flex items-center gap-2"><Brain className="w-5 h-5 text-brand-mint" /> Reasoning</CardTitle>
                            </CardHeader>
                            <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={reasoningScrollRefMobile}>
                              {reasoningEvents.length > 0 ? (
                                <div className="space-y-3">
                                  {reasoningEvents.map((r) => (
                                    <div key={r.id} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                                      <div className="flex items-center gap-2">
                                        <Avatar
                                          src={agentAvatars[r.playerId]?.avatarUrl}
                                          fallback={game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent"}
                                          size="sm"
                                          className="flex-shrink-0"
                                          type={agentAvatars[r.playerId]?.avatarType as any}
                                        />
                                        <div className="font-medium text-brand-teal text-xs">{game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent"}</div>
                                      </div>
                                      <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{r.reasoning}</div>
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
                                <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No reasoning yet</div>
                              )}
                            </CardContent>
                          </Card>

                          {/* Analysis */}
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center gap-2">
                                <Zap className="w-5 h-5 text-brand-mint" /> Analysis
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0 max-h-[300px] overflow-y-auto">
                              {allAnalyses.length > 0 ? (
                                <div className="space-y-3">
                                  {allAnalyses.map((analysis, idx) => (
                                    <div key={idx} className="space-y-2 pb-3 border-b last:border-b-0 last:pb-0">
                                      <div className="font-medium text-xs">Move {analysis.roundNumber}: {analysis.moveSan}</div>
                                      <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{analysis.narrative}</div>
                                      <div className="flex flex-wrap gap-2 text-xs">
                                        {analysis.bestMoveSan && (<span className="rounded-md bg-muted px-2 py-0.5">Best: {analysis.bestMoveSan}</span>)}
                                        {typeof analysis.evaluationCp === 'number' && (<span className="rounded-md bg-muted px-2 py-0.5">Eval: {(analysis.evaluationCp/100).toFixed(2)}</span>)}
                                        {analysis.isBrilliant && (<span className="rounded-md bg-brand-mint/20 text-brand-mint px-2 py-0.5">Brilliant</span>)}
                                        {analysis.isGood && (<span className="rounded-md bg-brand-mint/10 text-brand-mint px-2 py-0.5">Good</span>)}
                                        {analysis.isInaccuracy && (<span className="rounded-md bg-amber-100 text-amber-700 px-2 py-0.5">Inaccuracy</span>)}
                                        {analysis.isMistake && (<span className="rounded-md bg-orange-100 text-orange-700 px-2 py-0.5">Mistake</span>)}
                                        {analysis.isBlunder && (<span className="rounded-md bg-red-100 text-red-700 px-2 py-0.5">Blunder</span>)}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-xs text-muted-foreground">No analysis yet.</div>
                              )}
                            </CardContent>
                          </Card>

                          {/* Chat - ChatWindow has its own header */}
                          <Card className="h-[300px] flex flex-col overflow-hidden bg-violet-50/50 dark:bg-card">
                            <ChatWindow
                              messages={(game.events || [])
                                .filter((e: any) => e.type === 'chat_message')
                                .map((e: any) => ({
                                  playerId: e.player_id || e.playerId,
                                  message: e.message,
                                  timestamp: e.timestamp,
                                }))}
                              playerNames={game.players?.reduce((acc: Record<string, string>, p: any) => {
                                acc[p.id] = p.name || `Player ${p.id.slice(0, 8)}`;
                                return acc;
                              }, {}) || {}}
                              playerAvatars={agentAvatars}
                              onPlayerClick={(playerId) => {
                                const agentId = agentIdsByPlayerId[playerId];
                                if (agentId) showAgentProfile(agentId);
                              }}
                            />
                          </Card>
                        </div>
                      </TabsContent>
                    </CardContent>
                  </Tabs>
                </Card>
                )}


              </>
            ) : (
              <>
                {/* Desktop: Moves, Reasoning, Chat, and Analysis */}
                <div className="hidden md:flex md:flex-col md:gap-3 md:h-full md:overflow-hidden">
                  {/* Moves - fixed height at top */}
                  <Card className="2xl:hidden flex-shrink-0 h-[12vh] flex flex-col overflow-hidden">
                    <CardHeader className="pb-3 flex-shrink-0">
                      <CardTitle className="text-lg flex items-center gap-2"><ListOrdered className="w-5 h-5 text-brand-orange" /> Moves</CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-4 pb-4" ref={movesScrollRefMd}>
                      {moveEvents.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-muted-foreground text-xs">No moves yet.</div>
                      ) : (
                        <ol className="space-y-1 pl-4 list-decimal text-xs">
                          {moveEvents.map((m) => (
                            <li key={m.id} className="leading-snug">{m.text}</li>
                          ))}
                        </ol>
                      )}
                    </CardContent>
                  </Card>

                  {/* Agent Chat - takes ~50% of remaining space */}
                  <Card className="flex-1 flex flex-col overflow-hidden bg-violet-50/50 dark:bg-card">
                    <ChatWindow
                      messages={(game.events || [])
                        .filter((e: any) => e.type === 'chat_message')
                        .map((e: any) => ({
                          playerId: e.player_id || e.playerId,
                          message: e.message,
                          timestamp: e.timestamp,
                        }))}
                      playerNames={game.players?.reduce((acc: Record<string, string>, p: any) => {
                        acc[p.id] = p.name || `Player ${p.id.slice(0, 8)}`;
                        return acc;
                      }, {}) || {}}
                      playerAvatars={agentAvatars}
                      onPlayerClick={(playerId) => {
                        const agentId = agentIdsByPlayerId[playerId];
                        if (agentId) showAgentProfile(agentId);
                      }}
                    />
                  </Card>


                  {/* Reasoning (md–xl) — takes ~50% of remaining space when there is only the right column */}
                  <ReasoningCard
                    reasoningEvents={reasoningEvents}
                    playerInfo={Object.fromEntries(
                      (game.players || []).map((p: any) => [
                        p.id,
                        {
                          name: p.name || `Player ${p.id.slice(0, 8)}`,
                          avatarUrl: agentAvatars[p.id]?.avatarUrl,
                          avatarType: agentAvatars[p.id]?.avatarType,
                        },
                      ])
                    )}
                    onShowAgentProfile={(playerId) => {
                      const agentId = agentIdsByPlayerId[playerId];
                      if (agentId) showAgentProfile(agentId);
                    }}
                    onShowToolCalls={(toolCalls) => {
                      setSelectedToolCalls(toolCalls);
                      setToolCallsModalOpen(true);
                    }}
                    scrollRef={reasoningScrollRefMd}
                    className="2xl:hidden flex-1 flex flex-col overflow-hidden"
                    testId="reasoning-card-md"
                  />

                  <AnalysisCard
                    analyses={allAnalyses}
                    scrollRef={analysisScrollRef}
                    className="2xl:hidden flex-1 min-h-0 flex flex-col overflow-hidden"
                    testId="analysis-card-md"
                  />


                  <ReasoningCard
                    reasoningEvents={reasoningEvents}
                    playerInfo={Object.fromEntries(
                      (game.players || []).map((p: any) => [
                        p.id,
                        {
                          name: p.name || `Player ${p.id.slice(0, 8)}`,
                          avatarUrl: agentAvatars[p.id]?.avatarUrl,
                          avatarType: agentAvatars[p.id]?.avatarType,
                        },
                      ])
                    )}
                    onShowAgentProfile={(playerId) => {
                      const agentId = agentIdsByPlayerId[playerId];
                      if (agentId) showAgentProfile(agentId);
                    }}
                    onShowToolCalls={(toolCalls) => {
                      setSelectedToolCalls(toolCalls);
                      setToolCallsModalOpen(true);
                    }}
                    scrollRef={reasoningScrollRef2xl}
                    className="hidden 2xl:flex 2xl:flex-1 2xl:min-h-0 2xl:flex-col 2xl:overflow-hidden"
                    testId="reasoning-card-2xl"
                  />
                </div>

                {/* Mobile: Game/Info tabs (non-playground) — match playground structure */}
                {!isEmbedded && (
                <Card className="md:hidden">
                  <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full">
                    <CardHeader className="pb-3">
                      <TabsList className="grid w-full grid-cols-2 bg-muted p-1">
                        <TabsTrigger value="game" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                          <Zap className="w-4 h-4 mr-2" />
                          Game
                        </TabsTrigger>
                        <TabsTrigger value="info" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                          <Settings className="w-4 h-4 mr-2" />
                          Info
                          {(unreadChat + unreadEvents) > 0 && (
                            <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-orange px-1 text-[10px] text-white">
                              {unreadChat + unreadEvents}
                            </span>
                          )}
                        </TabsTrigger>
                      </TabsList>
                    </CardHeader>
                    <CardContent className="p-0">
                      {/* Game tab: show the board */}
                      <TabsContent value="game" className="mt-0">
                        <div className="px-2 py-4 space-y-3">
                          {/* Show clocks for real games */}
                          {!game?.isPlayground && stateView && (
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
                                <ChessClocks state={stateView} players={players} currentPlayerId={currentPlayerId} />
                              </div>
                            </div>
                          )}
                          {/* Board */}
                          <div className="flex items-center justify-center">
                            <ChessBoard
                              state={renderState}
                              onMoveSelected={(game?.isPlayground && !renderState.isFinished && !timeoutPending) ? handleMoveSelected : undefined}
                              lastMove={atLatest ? lastMove : null}
                              hideCapturedPieces={isEmbedded}
                              whitePlayerName={whitePlayerName}
                              blackPlayerName={blackPlayerName}
                              whiteRating={whiteRating}
                              blackRating={blackRating}
                              whitePlayerAvatar={players ? agentAvatars[players[0]] : undefined}
                              blackPlayerAvatar={players ? agentAvatars[players[1]] : undefined}
                              onWhitePlayerClick={players ? () => {
                                console.log('[ChessGame NonPlayground Mobile] White player clicked, players[0]:', players[0], 'agentId:', agentIdsByPlayerId[players[0]]);
                                const agentId = agentIdsByPlayerId[players[0]];
                                if (agentId) showAgentProfile(agentId);
                                else console.error('[ChessGame NonPlayground Mobile] No agentId for white player');
                              } : undefined}
                              onBlackPlayerClick={players ? () => {
                                console.log('[ChessGame NonPlayground Mobile] Black player clicked, players[1]:', players[1], 'agentId:', agentIdsByPlayerId[players[1]]);
                                const agentId = agentIdsByPlayerId[players[1]];
                                if (agentId) showAgentProfile(agentId);
                                else console.error('[ChessGame NonPlayground Mobile] No agentId for black player');
                              } : undefined}
                              flipped={userColor === 'black'}
                            />
                          </div>
                        </div>
                      </TabsContent>

                      {/* Info tab: Moves, Reasoning, Chat */}
                      <TabsContent value="info" className="mt-0">
                        <div className="space-y-3 px-2 pb-4">
                          {/* Moves */}
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center gap-2">
                                <ListOrdered className="w-5 h-5 text-brand-orange" /> Moves
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0 max-h-[220px] overflow-y-auto" ref={movesScrollRefMobile}>
                              {moveEvents.length === 0 ? (
                                <div className="text-xs text-muted-foreground">No moves yet.</div>
                              ) : (
                                <ol className="text-sm space-y-1 pl-4 list-decimal">
                                  {moveEvents.map((m) => (
                                    <li key={m.id} className="leading-snug">{m.text}</li>
                                  ))}
                                </ol>
                              )}
                            </CardContent>
                          </Card>

                          {/* Reasoning */}
                          <Card className="flex flex-col h-[260px] overflow-hidden">
                            <CardHeader className="p-0 px-4 md:px-6 pt-4 md:pt-6 pb-3 flex-shrink-0">
                              <CardTitle className="text-base flex items-center gap-2"><Brain className="w-5 h-5 text-brand-mint" /> Reasoning</CardTitle>
                            </CardHeader>
                            <CardContent className="flex-1 min-h-0 overflow-y-auto text-sm p-0 px-3 md:px-4 pt-2 pb-4" ref={reasoningScrollRefMobile}>
                              {reasoningEvents.length > 0 ? (
                                <div className="space-y-3">
                                  {reasoningEvents.map((r) => (
                                    <div key={r.id} className="space-y-1 pb-3 border-b last:border-b-0 last:pb-0">
                                      <div className="flex items-center gap-2">
                                        <Avatar
                                          src={agentAvatars[r.playerId]?.avatarUrl}
                                          fallback={game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent"}
                                          size="sm"
                                          className="flex-shrink-0"
                                          type={agentAvatars[r.playerId]?.avatarType as any}
                                        />
                                        <div className="font-medium text-brand-teal text-xs">{game.players?.find((p: any) => p.id === r.playerId)?.name || "Agent"}</div>
                                      </div>
                                      <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{r.reasoning}</div>
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
                                <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No reasoning yet</div>
                              )}
                            </CardContent>
                          </Card>

                          {/* Chat - ChatWindow has its own header */}
                          <Card className="h-[300px] flex flex-col overflow-hidden bg-violet-50/50 dark:bg-card">
                            <ChatWindow
                              messages={(game.events || [])
                                .filter((e: any) => e.type === 'chat_message')
                                .map((e: any) => ({
                                  playerId: e.player_id || e.playerId,
                                  message: e.message,
                                  timestamp: e.timestamp,
                                }))}
                              playerNames={game.players?.reduce((acc: Record<string, string>, p: any) => {
                                acc[p.id] = p.name || `Player ${p.id.slice(0, 8)}`;
                                return acc;
                              }, {}) || {}}
                              playerAvatars={agentAvatars}
                              onPlayerClick={(playerId) => {
                                const agentId = agentIdsByPlayerId[playerId];
                                if (agentId) showAgentProfile(agentId);
                              }}
                            />
                          </Card>

                          {/* Analysis */}
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center gap-2">
                                <Zap className="w-5 h-5 text-brand-mint" /> Analysis
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0 max-h-[300px] overflow-y-auto">
                              {allAnalyses.length > 0 ? (
                                <div className="space-y-3">
                                  {allAnalyses.map((analysis, idx) => (
                                    <div key={idx} className="space-y-2 pb-3 border-b last:border-b-0 last:pb-0">
                                      <div className="font-medium text-xs">Move {analysis.roundNumber}: {analysis.moveSan}</div>
                                      <div className="text-muted-foreground whitespace-pre-wrap break-words text-xs leading-relaxed">{analysis.narrative}</div>
                                      <div className="flex flex-wrap gap-2 text-xs">
                                        {analysis.bestMoveSan && (<span className="rounded-md bg-muted px-2 py-0.5">Best: {analysis.bestMoveSan}</span>)}
                                        {typeof analysis.evaluationCp === 'number' && (<span className="rounded-md bg-muted px-2 py-0.5">Eval: {(analysis.evaluationCp/100).toFixed(2)}</span>)}
                                        {analysis.isBrilliant && (<span className="rounded-md bg-brand-mint/20 text-brand-mint px-2 py-0.5">Brilliant</span>)}
                                        {analysis.isGood && (<span className="rounded-md bg-brand-mint/10 text-brand-mint px-2 py-0.5">Good</span>)}
                                        {analysis.isInaccuracy && (<span className="rounded-md bg-amber-100 text-amber-700 px-2 py-0.5">Inaccuracy</span>)}
                                        {analysis.isMistake && (<span className="rounded-md bg-orange-100 text-orange-700 px-2 py-0.5">Mistake</span>)}
                                        {analysis.isBlunder && (<span className="rounded-md bg-red-100 text-red-700 px-2 py-0.5">Blunder</span>)}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-xs text-muted-foreground">No analysis yet.</div>
                              )}
                            </CardContent>
                          </Card>
                        </div>
                      </TabsContent>
                    </CardContent>
                  </Tabs>
                </Card>
                )}

              </>
            )}
          </div>
        </div>
      ) : usedGameId ? (
        <Card>
          <CardContent className="py-10 text-center text-sm opacity-70">Loading game…</CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card className="rounded-lg">
            <CardHeader className="flex items-center justify-between">
              <CardTitle>Your Active Chess Games</CardTitle>

              <Button
                variant="outline"
                size="sm"
                className="rounded-md"
                disabled={gamesLoading}
                onClick={() => void (async () => {
                  setGamesLoading(true);
                  try { setUserGames(await ChessApiService.getUserGames(false)); }
                  catch { /* handled elsewhere */ }
                  finally { setGamesLoading(false); }
                })()}
              >
                {gamesLoading ? 'Loading…' : 'Refresh'}
              </Button>
            </CardHeader>
            <CardContent>
              {gamesLoading ? (
                <div className="text-sm opacity-70">Loading…</div>
              ) : userGames.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-muted-foreground mb-4">No active games yet.</p>
                  <Button
                    className="rounded-md bg-brand-teal hover:bg-brand-teal/90"
                    onClick={() => navigate('/games')}
                  >
                    Find a Match
                  </Button>
                </div>
              ) : (
                <ul className="space-y-2">
                  {userGames.map((g) => {
                    const result = getGameResult(g, currentPlayerId);
                    return (
                      <li key={g.id} className="flex items-center justify-between border rounded-md p-3">
                        <div className="flex items-center gap-3">
                          <div>
                            <div className="text-sm font-medium">Game {String(g.id)}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {g.state.isFinished ? (
                                <Badge
                                  variant={result.variant === 'success' ? 'default' : result.variant === 'destructive' ? 'destructive' : 'secondary'}
                                  className={result.variant === 'success' ? 'bg-green-100 text-green-800 border-green-200' : ''}
                                >
                                  {result.text}
                                </Badge>
                              ) : (
                                'In Progress'
                              )}
                            </div>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          className="rounded-md"
                          onClick={() => navigate(`/games/chess/${g.id}`)}
                        >
                          {g.state.isFinished ? 'View' : 'Continue'}
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <AgentProfileModal
        agentId={selectedAgentId}
        open={isProfileOpen}
        onOpenChange={closeAgentProfile}
      />

      <ToolCallsModal
        open={toolCallsModalOpen}
        onOpenChange={setToolCallsModalOpen}
        toolCalls={selectedToolCalls}
        agentName={selectedAgentName}
      />

      <GameVictoryModal
        open={victoryModalOpen}
        onOpenChange={setVictoryModalOpen}
        isVictory={isVictory}
        gameId={String(game?.id || '')}
        gameType="chess"
        endReason={gameEndReason}
      />
    </div>
  );
};

export default ChessGame;
