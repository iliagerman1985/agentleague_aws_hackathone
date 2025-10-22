import { api } from '@/lib/api';
import type { AgentVersionId, GameId, PlayerId, EventId } from '@/types/ids';
import type { ChessPossibleMoves, ChessStateView, ChessState, Color } from '@/types/chess';
import { GameApiService } from './gameApi';

// ===== ENUMS =====
export enum ChessEventType {
  GAME_INITIALIZED = 'game_initialized',
  PLAYER_JOINED = 'player_joined',
  MOVE_PLAYED = 'move_played',
  CHECK = 'check',
  CHECKMATE = 'checkmate',
  STALEMATE = 'stalemate',
  GAME_FINISHED = 'game_finished',
  MOVE_ANALYSIS = 'move_analysis'
}

export type ChessPlaygroundOpponent = 'brain' | 'self';
export type ChessSide = 'white' | 'black';

// ===== EVENTS =====
export interface BaseChessEvent {
  id: EventId;
  type: ChessEventType;
  timestamp: number;
  roundNumber: number;
}

export interface GameInitializedEvent extends BaseChessEvent {
  type: ChessEventType.GAME_INITIALIZED;
  gameId: GameId;
}

export interface PlayerJoinedEvent extends BaseChessEvent {
  type: ChessEventType.PLAYER_JOINED;
  playerId: PlayerId;
  agentVersionId: AgentVersionId;
  name: string;
}

export interface MovePlayedEvent extends BaseChessEvent {
  type: ChessEventType.MOVE_PLAYED;
  playerId: PlayerId;
  fromSquare: string;
  toSquare: string;
  promotion?: 'q' | 'r' | 'b' | 'n' | null;
  isCapture: boolean;
}

export interface CheckEvent extends BaseChessEvent {
  type: ChessEventType.CHECK;
  sideInCheck: Color;
}

export interface CheckmateEvent extends BaseChessEvent {
  type: ChessEventType.CHECKMATE;
  winner: PlayerId;
}

export interface StalemateEvent extends BaseChessEvent {
  type: ChessEventType.STALEMATE;
  reason?: string;
}

export interface GameFinishedEvent extends BaseChessEvent {
  type: ChessEventType.GAME_FINISHED;
  winner?: PlayerId;
  drawReason?: string;
}
export interface MoveAnalysisEvent extends BaseChessEvent {
  type: ChessEventType.MOVE_ANALYSIS;
  playerId: PlayerId;
  move_san: string;
  evaluation_cp?: number | null;
  evaluation_mate?: number | null;
  best_move_san?: string | null;
  narrative: string;
  is_blunder?: boolean;
  is_mistake?: boolean;
  is_inaccuracy?: boolean;
  is_brilliant?: boolean;
  is_good?: boolean;
}


export type ChessEvent =
  | GameInitializedEvent
  | PlayerJoinedEvent
  | MovePlayedEvent
  | CheckEvent
  | CheckmateEvent
  | StalemateEvent
  | GameFinishedEvent
  | MoveAnalysisEvent;

// ===== BACKEND WIRE TYPES =====
export interface CreateGameRequest {
  gameType: 'chess';
  config: Record<string, any>;
  agentIds: AgentVersionId[];
}

export interface CreateGameResponse {
  game_id: GameId;
  message: string;
}

export interface CreatePlaygroundRequest {
  agentId: AgentVersionId;
  config: Record<string, any>;
  opponent: ChessPlaygroundOpponent;
  userSide?: ChessSide;
}

export interface ChessFromFENRequest {
  agentId: AgentVersionId;
  fen: string;
  config?: Record<string, any>;
  opponent: ChessPlaygroundOpponent;
  userSide?: ChessSide;
}

export interface ChessFromMovesRequest {
  agentId: AgentVersionId;
  moves: string; // SAN/PGN-like string
  config?: Record<string, any>;
  opponent: ChessPlaygroundOpponent;
  userSide?: ChessSide;
}

export interface ChessFromStateRequest {
  agentId: AgentVersionId;
  stateView: Record<string, any>; // Chess state view JSON
  config?: Record<string, any>;
  opponent: ChessPlaygroundOpponent;
  userSide?: ChessSide;
}

export interface ConvertFENRequest {
  fen: string;
}

export interface ConvertMovesRequest {
  moves: string;
}

export interface ConvertStateResponse {
  state: Record<string, any>;
}

export interface GameStateResponse {
  id: GameId;
  gameType: 'chess' | string;
  state: ChessState;
  events: ChessEvent[];
  config: Record<string, any>;
  version: number;
  isPlayground: boolean;
  matchmakingStatus?: string | null;
  players: Array<{
    id: PlayerId;
    agentVersionId: AgentVersionId;
    name: string;
    username?: string | null;
    displayName?: string | null;
    rating?: number | null;
    color?: ChessSide | null;
  }>;
}

export interface TurnResultResponse {
  gameId: GameId;
  newState: ChessState; // inner object uses snake_case keys (backend returns python-mode dict)
  newEvents: ChessEvent[];
  isFinished: boolean;
  currentPlayerId?: PlayerId | null;
  newCoinsBalance?: number | null; // Updated coins balance after consuming tokens (for playground moves)
}

// Backend wire format for moves (camelCase to match JsonModel serialization)
export interface ChessMoveDataWire {
  fromSquare: string;
  toSquare: string;
  promotion?: 'q' | 'r' | 'b' | 'n' | null;
}

// ===== SERVICE =====
export class ChessApiService {
  /** Create a new Chess game */
  static async createGame(request: CreateGameRequest): Promise<CreateGameResponse> {
    const wire = { game_type: request.gameType, config: request.config, agent_ids: request.agentIds };
    return api.post('/api/v1/games', wire);
  }

  /** Create a 2-player Chess playground using the same agent for both sides */
  static async createPlayground(request: CreatePlaygroundRequest): Promise<GameStateResponse> {
    const wire = { agent_id: request.agentId, config: request.config, opponent: request.opponent, user_side: request.userSide };
    return api.post('/api/v1/games/playground/chess', wire);
  }

  /** Create a Chess playground from a FEN position */
  static async createPlaygroundFromFEN(request: ChessFromFENRequest): Promise<GameStateResponse> {
    const wire = { agent_id: request.agentId, fen: request.fen, config: request.config, opponent: request.opponent, user_side: request.userSide };
    return api.post('/api/v1/games/playground/chess/from_fen', wire);
  }

  /** Create a Chess playground from a SAN/PGN move list */
  static async createPlaygroundFromMoves(request: ChessFromMovesRequest): Promise<GameStateResponse> {
    const wire = { agent_id: request.agentId, moves: request.moves, config: request.config, opponent: request.opponent, user_side: request.userSide };
    return api.post('/api/v1/games/playground/chess/from_moves', wire);
  }

  /** Create a Chess playground from a JSON state view */
  static async createPlaygroundFromState(request: ChessFromStateRequest): Promise<GameStateResponse> {
    const wire = { agent_id: request.agentId, state_view: request.stateView, config: request.config, opponent: request.opponent, user_side: request.userSide };
    return api.post('/api/v1/games/playground/chess/from_state', wire);
  }

  /** Get current game state with optional long polling */
  static async getGameState(
    gameId: GameId,
    currentVersion?: number,
    timeout?: number
  ): Promise<GameStateResponse> {
    const params = new URLSearchParams();
    if (currentVersion !== undefined) {
      params.append('current_version', currentVersion.toString());
    }
    if (timeout !== undefined) {
      params.append('timeout', timeout.toString());
    }

    const queryString = params.toString();
    const endpoint = queryString ? `/api/v1/games/${gameId}?${queryString}` : `/api/v1/games/${gameId}`;

    // Use longer timeout for long polling requests (add a generous buffer)
    const requestTimeout = timeout ? (timeout + 10) * 1000 : undefined;

    return api.get(endpoint, { timeout: requestTimeout });
  }

  /** Get current user's games filtered to chess */
  static async getUserGames(includeFinished: boolean = false): Promise<GameStateResponse[]> {
    const params = new URLSearchParams();
    params.append('game_type', 'chess');
    if (!includeFinished) {
      // Backend route uses only_active flag; default is true so no need to set
    }
    const url = `/api/v1/games?${params.toString()}`;
    return api.get(url);
  }

  /** Execute a turn in the chess game; optionally provide a move override */
  static async executeTurn(gameId: GameId, playerId: PlayerId, moveOverride?: ChessMoveDataWire | null, turn?: number): Promise<TurnResultResponse> {
    // Convert frontend camelCase move to wire format (also camelCase to match backend JsonModel)
    const wireMove: ChessMoveDataWire | null = moveOverride ? {
      fromSquare: moveOverride.fromSquare,
      toSquare: moveOverride.toSquare,
      promotion: moveOverride.promotion ?? null,
    } : null;

    const body = {
      playerId: playerId,
      turn: turn,
      moveOverride: wireMove,
    };
    // Use 5-minute timeout to accommodate agent thinking and tool calls
    return api.post(`/api/v1/games/${gameId}/turns`, body, { timeout: 300000 });
  }

  /** Finalize a chess game due to timeout */
  static async finalizeTimeout(gameId: GameId, playerId: PlayerId): Promise<TurnResultResponse> {
    return api.post(`/api/v1/games/${gameId}/timeout`, { player_id: playerId });
  }

  /** Convenience: request legal moves for a player from the current state on client */
  static async getPossibleMovesFromState(_state: ChessStateView, _playerId: PlayerId): Promise<ChessPossibleMoves | null> {
    // This is a client-side helper for future use; the server is the source of truth.
    // For now, return null to indicate we rely on server-provided possible moves.
    return null;
  }

  /** Convert FEN to chess state view for preview */
  static async convertFENToState(request: ConvertFENRequest): Promise<ConvertStateResponse> {
    return api.post('/api/v1/games/chess/convert_fen', request);
  }

  /** Convert moves to chess state view for preview */
  static async convertMovesToState(request: ConvertMovesRequest): Promise<ConvertStateResponse> {
    return api.post('/api/v1/games/chess/convert_moves', request);
  }

  /** Delete a chess game */
  static async deleteGame(gameId: GameId): Promise<void> {
    return GameApiService.deleteGame(gameId);
  }

  /** Get reconstructed game state at a specific event index for replay */
  static async getStateAtEvent(gameId: GameId, eventIndex: number): Promise<GameStateResponse> {
    return api.get(`/api/v1/games/chess/${gameId}/state_at_event/${eventIndex}`);
  }
}
