import { useMemo } from "react";

import { ChessBoard } from "@/components/chess/ChessBoard";
import { EditableChessBoard } from "@/components/chess/EditableChessBoard";
import type { ChessStateView, Color } from "@/types/chess";
import { PokerTable } from "@/components/poker/PokerTable";
import type { AgentVersionId } from "@/types/ids";
import { GameEnvironment } from "@/services/agentsService";

export interface GameStatePreviewProps {
  environment: GameEnvironment;
  jsonText: string;
  onJsonChange?: (text: string) => void;
  editable?: boolean;
  hideCapturedPieces?: boolean;
  size?: 'small' | 'medium' | 'large';
}

interface ParseResult {
  parsed: any | null;
  error: string | null;
  isInitial: boolean;
}

function useParsedState(text: string): ParseResult {
  return useMemo(() => {
    const normalized = (text ?? "").replace(/\s/g, "");
    const isInitial = normalized === "" || normalized === "{}";
    try {
      // treat empty as empty object
      const cleaned = text?.trim().length ? text : "{}";
      const parsed = JSON.parse(cleaned);
      return { parsed, error: null, isInitial };
    } catch (e: any) {
      return { parsed: null, error: "Invalid JSON", isInitial };
    }
  }, [text]);
}

function initialChess(): ChessStateView {
  const back = (color: Color) => (['rook','knight','bishop','queen','king','bishop','knight','rook'] as const)
    .map((t) => ({ type: t, color } as const));
  const pawns = (color: Color) => Array.from({ length: 8 }, () => ({ type: 'pawn', color } as const));
  const emptyRows = Array.from({ length: 4 }, () => Array(8).fill(null));
  return {
    board: [back('black') as any, pawns('black') as any, ...emptyRows, pawns('white') as any, back('white') as any] as any,
    sideToMove: 'white',
    castlingRights: { whiteKingside: true, whiteQueenside: true, blackKingside: true, blackQueenside: true },
    enPassantSquare: null,
    halfmoveClock: 0,
    fullmoveNumber: 1,
    remainingTimeMs: {} as any,
    lastTimestampMs: null,
    capturedPieces: { white: [], black: [] },
    materialAdvantage: 0,
    isFinished: false,
    winner: null,
    drawReason: null,
  };
}

function renderChess(state: any | undefined, editable: boolean, hideCapturedPieces: boolean, size: 'small' | 'medium' | 'large', onChange?: (newState: ChessStateView) => void) {
  const candidate: ChessStateView | undefined = state && state.board ? state as ChessStateView : undefined;
  const toShow: ChessStateView = candidate ?? initialChess();

  if (editable && onChange) {
    return (
      <div className="relative">
        <EditableChessBoard state={toShow} onStateChange={onChange} />
      </div>
    );
  }

  return (
    <div className="relative">
      <ChessBoard state={toShow} hideCapturedPieces={hideCapturedPieces} size={size} />
    </div>
  );
}

function renderPoker(state?: any) {
  // Expecting shape similar to TexasHoldemState(StatePlayerView). Use extremely tolerant mapping.
  const s = state ?? {};
  const communityCards = Array.isArray(s.community_cards) ? s.community_cards : [];
  const pot = typeof s.pot === 'number' ? s.pot : 0;
  const players = Array.isArray(s.players) ? s.players.map((p: any, i: number) => ({
    id: (p.agent_id ?? `p${i}`) as AgentVersionId,
    name: p.name ?? `P${i + 1}`,
    chipCount: typeof p.chips === 'number' ? p.chips : 0,
    position: (typeof p.position === 'number' ? p.position : i + 1),
  })) : [];

  return (
    <PokerTable
      players={players}
      communityCards={communityCards}
      pot={pot}
      onAction={() => { /* no-op in preview */ }}
      onAgentTurn={() => { /* no-op in preview */ }}
    />
  );
}

/**
 * Convert chess board from map format (dict) to 2D array format.
 * Map format: {"a1": {type: "rook", color: "white"}, ...}
 * Array format: [[piece, piece, ...], [piece, piece, ...], ...]
 */
function convertBoardMapToArray(boardMap: Record<string, any>): (any | null)[][] {
  const board: (any | null)[][] = Array.from({ length: 8 }, () => Array(8).fill(null));

  for (const [coord, piece] of Object.entries(boardMap)) {
    if (coord.length !== 2) continue;

    const file = coord.charCodeAt(0) - 97; // a=0, b=1, ..., h=7
    const rank = parseInt(coord[1], 10); // 1-8

    if (file < 0 || file > 7 || rank < 1 || rank > 8) continue;

    // Convert to array indices: rank 8 -> row 0, rank 1 -> row 7
    const row = 8 - rank;
    const col = file;

    board[row][col] = piece;
  }

  return board;
}

function toEnvView(environment: GameEnvironment, parsed: any | null): { view: any | null; invalid: boolean } {
  // Allow multiple nesting levels:
  // 1. Direct state object: { board: {...}, sideToMove: ... }
  // 2. Wrapped in state: { state: { board: {...}, ... } }
  // 3. Tool execution format: { body: { context: { state: { board: {...}, ... } } } }
  let raw = null;
  if (parsed && typeof parsed === 'object') {
    // Try to extract state from various nesting levels
    if (parsed.body?.context?.state) {
      raw = parsed.body.context.state;
    } else if (parsed.context?.state) {
      raw = parsed.context.state;
    } else if (parsed.state) {
      raw = parsed.state;
    } else {
      raw = parsed;
    }
  }
  if (!raw) return { view: null, invalid: true };

  if (environment === GameEnvironment.CHESS) {
    // Support both formats: 2D array (old) and map/dict (new)
    if (Array.isArray(raw.board) && raw.board.length === 8) {
      // Already in 2D array format
      return { view: raw, invalid: false };
    } else if (typeof raw.board === 'object' && !Array.isArray(raw.board)) {
      // Map format - convert to 2D array for rendering
      try {
        const convertedBoard = convertBoardMapToArray(raw.board);
        return { view: { ...raw, board: convertedBoard }, invalid: false };
      } catch (e) {
        return { view: null, invalid: true };
      }
    }
    return { view: null, invalid: true };
  }
  if (environment === GameEnvironment.TEXAS_HOLDEM) {
    // Minimal sanity: allow any object; renderer is resilient
    return { view: raw, invalid: false };
  }
  return { view: raw, invalid: false };
}

export function GameStatePreview({ environment, jsonText, onJsonChange, editable = false, hideCapturedPieces = false, size = 'large' }: GameStatePreviewProps) {
  const { parsed, error, isInitial } = useParsedState(jsonText);
  const { view, invalid } = useMemo(() => toEnvView(environment, parsed), [environment, parsed]);

  const showError = (!!error || invalid) && !isInitial;

  const handleChessStateChange = (newState: ChessStateView) => {
    if (onJsonChange) {
      const updatedJson = JSON.stringify(newState, null, 2);
      onJsonChange(updatedJson);
    }
  };

  return (
    <div className="relative p-1">
      {/* Visual renderer by environment */}
      {environment === GameEnvironment.CHESS && renderChess(view ?? undefined, editable, hideCapturedPieces, size, handleChessStateChange)}
      {environment === GameEnvironment.TEXAS_HOLDEM && renderPoker(view ?? undefined)}

      {/* Error overlay */}
      {showError && (
        <div className="absolute top-3 left-3 z-10 rounded bg-red-600 text-white text-xs px-2 py-1 shadow">
          Invalid or incomplete JSON — showing initial state
        </div>
      )}
    </div>
  );
}

