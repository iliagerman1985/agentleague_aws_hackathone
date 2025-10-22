import type { PlayerId } from '@/types/ids';

export type Color = 'white' | 'black';

export interface CastlingRights {
  whiteKingside: boolean;
  whiteQueenside: boolean;
  blackKingside: boolean;
  blackQueenside: boolean;
}

export interface ChessPiece {
  type: 'king' | 'queen' | 'rook' | 'bishop' | 'knight' | 'pawn';
  color: Color;
}

export type PieceType = 'king' | 'queen' | 'rook' | 'bishop' | 'knight' | 'pawn';

export interface ChessStateView {
  board: (ChessPiece | null)[][];
  sideToMove: Color;
  castlingRights: CastlingRights;
  enPassantSquare: string | null;
  halfmoveClock: number;
  fullmoveNumber: number;
  remainingTimeMs: Record<PlayerId, number>;
  lastTimestampMs: number | null;
  capturedPieces: Record<Color, PieceType[]>;
  materialAdvantage: number;
  isFinished: boolean;
  winner: PlayerId | null;
  drawReason: string | null;
  forfeitReason?: string | null;
}

export interface ChessPossibleMove {
  fromSquare: string;
  toSquare: string;
  piece: PieceType;
  isCheck: boolean;
  promotion?: Array<'q' | 'r' | 'b' | 'n'> | null;
}

export interface ChessPossibleMoves {
  possibleMoves: ChessPossibleMove[];
}

export interface ChessMoveData {
  fromSquare: string;
  toSquare: string;
  promotion?: 'q' | 'r' | 'b' | 'n';
}

// Full state returned by server (includes base game fields)
export interface ChessState extends ChessStateView {
  currentPlayerId: PlayerId;
  turn: number;
}
