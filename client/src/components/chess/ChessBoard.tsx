import React, { useMemo, useState } from 'react';
import type { ChessPossibleMoves, ChessStateView, ChessMoveData } from '@/types/chess';
import { ChessPieceView } from './ChessPiece';
import { ChessSquare } from './ChessSquare';
import { Avatar } from '@/components/common/Avatar';
import { CapturedPieces } from './CapturedPieces';

function idxToSquare(r: number, c: number): string {
  return String.fromCharCode(97 + c) + String(8 - r);
}

function squareToIdx(square: string): { r: number; c: number } {
  const file = square.charCodeAt(0) - 97; // a=0
  const rank = parseInt(square[1]!, 10);
  return { r: 8 - rank, c: file };
}

export interface ChessBoardProps {
  state: ChessStateView;
  possibleMoves?: ChessPossibleMoves | null;
  onMoveSelected?: (move: ChessMoveData) => void;
  lastMove?: { from: string; to: string } | null;
  hideCapturedPieces?: boolean;
  whitePlayerName?: string;
  blackPlayerName?: string;
  whiteRating?: number | string | null;
  blackRating?: number | string | null;
  whitePlayerAvatar?: { avatarUrl?: string | null; avatarType?: string };
  blackPlayerAvatar?: { avatarUrl?: string | null; avatarType?: string };
  onWhitePlayerClick?: () => void;
  onBlackPlayerClick?: () => void;
  size?: 'small' | 'medium' | 'large';
  flipped?: boolean; // When true, render from black's perspective (8th rank at bottom)
}

export const ChessBoard: React.FC<ChessBoardProps> = ({
  state,
  possibleMoves,
  onMoveSelected,
  lastMove,
  hideCapturedPieces = false,
  whitePlayerName,
  blackPlayerName,
  whiteRating,
  blackRating,
  whitePlayerAvatar,
  blackPlayerAvatar,
  onWhitePlayerClick,
  onBlackPlayerClick,
  size = 'large',
  flipped = false
}) => {
  const [selectedFrom, setSelectedFrom] = useState<string | null>(null);

  const sizeClass = size === 'small' ? 'max-w-sm' : size === 'medium' ? 'max-w-md' : 'max-w-full';

  const movesByFrom = useMemo(() => {
    const map = new Map<string, string[]>();
    if (!possibleMoves?.possibleMoves) return map;
    for (const mv of possibleMoves.possibleMoves) {
      const arr = map.get(mv.fromSquare) ?? [];
      arr.push(mv.toSquare);
      map.set(mv.fromSquare, arr);
    }
    return map;
  }, [possibleMoves]);

  // Generate board squares in the correct order based on flipped state
  const boardSquares = useMemo(() => {
    const squares: Array<{ r: number; c: number; coord: string; cell: any }> = [];

    if (flipped) {
      // Black's perspective: iterate rows from 7 to 0 (8th rank to 1st rank)
      for (let r = 7; r >= 0; r--) {
        // Iterate columns from 7 to 0 (h-file to a-file)
        for (let c = 7; c >= 0; c--) {
          const coord = idxToSquare(r, c);
          const cell = state.board[r]?.[c] ?? null;
          squares.push({ r, c, coord, cell });
        }
      }
    } else {
      // White's perspective: iterate rows from 0 to 7 (1st rank to 8th rank)
      for (let r = 0; r < 8; r++) {
        // Iterate columns from 0 to 7 (a-file to h-file)
        for (let c = 0; c < 8; c++) {
          const coord = idxToSquare(r, c);
          const cell = state.board[r]?.[c] ?? null;
          squares.push({ r, c, coord, cell });
        }
      }
    }

    return squares;
  }, [state.board, flipped]);

  const handleSquareClick = (coord: string) => {
    const { r, c } = squareToIdx(coord);
    const piece = state.board[r]?.[c] ?? null;
    console.debug('[ChessBoard] click', { coord, piece, sideToMove: state.sideToMove });

    if (!selectedFrom) {
      if (piece && piece.color === state.sideToMove) {
        console.debug('[ChessBoard] select from', coord);
        setSelectedFrom(coord);
      }
      return;
    }

    // If clicking same-side piece, change selection
    if (piece && piece.color === state.sideToMove) {
      console.debug('[ChessBoard] change selection', { from: selectedFrom, to: coord });
      setSelectedFrom(coord);
      return;
    }

    // Attempt to make a move from selectedFrom -> coord
    // If possibleMoves is provided, only allow legal targets; otherwise optimistically send the move
    let canAttempt = true;
    if (possibleMoves) {
      const legalTargets = movesByFrom.get(selectedFrom) ?? [];
      canAttempt = legalTargets.includes(coord);
      console.debug('[ChessBoard] legality check', { from: selectedFrom, to: coord, legal: canAttempt });
    }
    if (canAttempt && coord !== selectedFrom) {
      console.debug('[ChessBoard] attempt move', { from: selectedFrom, to: coord });
      onMoveSelected?.({ fromSquare: selectedFrom, toSquare: coord });
      // Keep selection so the user can try a different target if the move is rejected by the server
      return;
    }
    // Toggle off if user clicked the same square
    if (coord === selectedFrom) {
      setSelectedFrom(null);
      console.debug('[ChessBoard] clear selection');
    }
  };

  // Determine which player should be on top and bottom based on flipped state
  const topPlayerName = flipped ? whitePlayerName : blackPlayerName;
  const topPlayerRating = flipped ? whiteRating : blackRating;
  const topPlayerAvatar = flipped ? whitePlayerAvatar : blackPlayerAvatar;
  const topPlayerClick = flipped ? onWhitePlayerClick : onBlackPlayerClick;
  const topPlayerColor = flipped ? 'white' : 'black';
  const topPlayerMaterialAdvantage = flipped ? state.materialAdvantage : -state.materialAdvantage;
  const topPlayerCapturedPieces = flipped ? (state.capturedPieces?.white ?? []) : (state.capturedPieces?.black ?? []);

  const bottomPlayerName = flipped ? blackPlayerName : whitePlayerName;
  const bottomPlayerRating = flipped ? blackRating : whiteRating;
  const bottomPlayerAvatar = flipped ? blackPlayerAvatar : whitePlayerAvatar;
  const bottomPlayerClick = flipped ? onBlackPlayerClick : onWhitePlayerClick;
  const bottomPlayerColor = flipped ? 'black' : 'white';
  const bottomPlayerMaterialAdvantage = flipped ? -state.materialAdvantage : state.materialAdvantage;
  const bottomPlayerCapturedPieces = flipped ? (state.capturedPieces?.black ?? []) : (state.capturedPieces?.white ?? []);

  return (
    <div className="w-full flex justify-center px-2 md:px-4">
      <div className={`flex flex-col items-center gap-2 md:gap-3 w-full mx-auto ${sizeClass}`}>


        {/* Top player stats */}
        {!hideCapturedPieces && (
          <div className="w-full flex items-center justify-between text-xs sm:text-sm pl-5 pr-2 md:pl-6 md:pr-3">
            <div className="flex items-center gap-2">
              <div
                className={topPlayerClick ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}
                onClick={topPlayerClick}
              >
                <Avatar
                  src={topPlayerAvatar?.avatarUrl}
                  fallback={topPlayerName ?? (topPlayerColor === 'white' ? 'White' : 'Black')}
                  size="lg"
                  type={topPlayerAvatar?.avatarType as any}
                  showBorder={true}
                />
              </div>
              <div className="font-medium">
                <span
                  className={topPlayerClick ? "cursor-pointer hover:text-brand-teal transition-colors" : ""}
                  onClick={topPlayerClick}
                >
                  {topPlayerName ?? (topPlayerColor === 'white' ? 'White' : 'Black')}
                </span>
                <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 text-[10px] uppercase tracking-wide">
                  {topPlayerColor === 'white' ? 'White' : 'Black'}
                </span>
                <span className="ml-2 text-muted-foreground">Rating {String(topPlayerRating ?? "—")}</span>
              </div>
            </div>
            <div className="flex items-center gap-3 text-muted-foreground">
              <span>Score {topPlayerMaterialAdvantage >= 0 ? `+${topPlayerMaterialAdvantage}` : String(topPlayerMaterialAdvantage)}</span>
              <span>Pieces {topPlayerCapturedPieces.length}</span>
              <span>Points {(() => {
                const vals: Record<string, number> = { pawn: 1, knight: 3, bishop: 3, rook: 5, queen: 9 };
                return topPlayerCapturedPieces.reduce((s, p) => s + (vals[p] ?? 0), 0);
              })()}</span>
            </div>
          </div>
        )}

        {/* Chess board with captured pieces on sides */}
        <div className="w-full flex items-end justify-center gap-2 md:gap-3">
          {/* Left side - User's captured pieces (pieces they lost) */}
          {!hideCapturedPieces && (
            <div className="flex-shrink-0 flex items-end pb-2.5 md:pb-3">
              <CapturedPieces
                capturedByWhite={state.capturedPieces?.white ?? []}
                capturedByBlack={state.capturedPieces?.black ?? []}
                materialAdvantage={state.materialAdvantage ?? 0}
                layout="vertical"
                side={bottomPlayerColor}
              />
            </div>
          )}

          {/* Chess board */}
          <div
            className="aspect-square w-full flex-shrink-0 transition-[max-width] duration-300 ease-in-out board-max"
          >
            <div className="relative w-full h-full px-1.5 md:px-2 pt-1.5 md:pt-2 pb-2.5 md:pb-3">
              {/* Board grid */}
              <div className="absolute top-2 right-2 bottom-5 left-5 md:top-3 md:right-3 md:bottom-6 md:left-6 grid grid-cols-8 grid-rows-8 rounded-xl overflow-hidden border border-brand-teal/60 shadow-sm bg-white/40 dark:bg-white/5 backdrop-blur-sm">
                {boardSquares.map(({ r, c, coord, cell }) => {
                  const isLight = (r + c) % 2 === 0;
                  const isSelected = selectedFrom === coord;
                  const isTarget = selectedFrom ? (movesByFrom.get(selectedFrom)?.includes(coord) ?? false) : false;
                  return (
                    <ChessSquare
                      key={coord}
                      coord={coord}
                      isLight={isLight}
                      selected={isSelected}
                      isMoveTarget={isTarget}
                      isLastFrom={lastMove ? lastMove.from === coord : false}
                      isLastTo={lastMove ? lastMove.to === coord : false}
                      onClick={() => handleSquareClick(coord)}
                    >
                      {cell ? <ChessPieceView piece={cell} /> : null}
                    </ChessSquare>
                  );
                })}
              </div>

              {/* File labels (a–h or h–a) below board */}
              <div className="pointer-events-none absolute bottom-0 left-5 right-2 md:left-6 md:right-3 h-6 grid grid-cols-8 text-[8px] sm:text-[10px] md:text-xs font-medium text-gray-700/80 dark:text-gray-200/80 z-10">
                {Array.from({ length: 8 }, (_, i) => flipped ? String.fromCharCode(104 - i) : String.fromCharCode(97 + i)).map((f) => (
                  <span key={f} className="text-center flex items-center justify-center">{f}</span>
                ))}
              </div>
              {/* Rank labels (8–1 or 1–8) to the left of board */}
              <div className="pointer-events-none absolute left-0 top-2 bottom-5 md:top-3 md:bottom-6 w-5 md:w-6 grid grid-rows-8 text-[8px] sm:text-[10px] md:text-xs font-medium text-gray-700/80 dark:text-gray-200/80 z-10">
                {Array.from({ length: 8 }, (_, i) => flipped ? String(i + 1) : String(8 - i)).map((n) => (
                  <span key={n} className="flex items-center justify-center h-full">{n}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Right side - Opponent's captured pieces (pieces they lost) */}
          {!hideCapturedPieces && (
            <div className="flex-shrink-0 flex items-end pb-2.5 md:pb-3">
              <CapturedPieces
                capturedByWhite={state.capturedPieces?.white ?? []}
                capturedByBlack={state.capturedPieces?.black ?? []}
                materialAdvantage={state.materialAdvantage ?? 0}
                layout="vertical"
                side={topPlayerColor}
              />
            </div>
          )}
        </div>

        {/* Bottom player stats */}
        {!hideCapturedPieces && (
          <div className="w-full pl-5 pr-2 md:pl-6 md:pr-3 mt-2">
            <div className="flex items-center justify-between text-xs sm:text-sm">
              <div className="flex items-center gap-2">
                <div
                  className={bottomPlayerClick ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}
                  onClick={bottomPlayerClick}
                >
                  <Avatar
                    src={bottomPlayerAvatar?.avatarUrl}
                    fallback={bottomPlayerName ?? (bottomPlayerColor === 'white' ? 'White' : 'Black')}
                    size="lg"
                    type={bottomPlayerAvatar?.avatarType as any}
                    showBorder={true}
                  />
                </div>
                <div className="font-medium">
                  <span
                    className={bottomPlayerClick ? "cursor-pointer hover:text-brand-teal transition-colors" : ""}
                    onClick={bottomPlayerClick}
                  >
                    {bottomPlayerName ?? (bottomPlayerColor === 'white' ? 'White' : 'Black')}
                  </span>
                  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 text-[10px] uppercase tracking-wide">
                    {bottomPlayerColor === 'white' ? 'White' : 'Black'}
                  </span>
                  <span className="ml-2 text-muted-foreground">Rating {String(bottomPlayerRating ?? "\u2014")}</span>
                </div>
              </div>
              <div className="flex items-center gap-3 text-muted-foreground">
                <span>Score {bottomPlayerMaterialAdvantage >= 0 ? `+${bottomPlayerMaterialAdvantage}` : String(bottomPlayerMaterialAdvantage)}</span>
                <span>Pieces {bottomPlayerCapturedPieces.length}</span>
                <span>Points {(() => {
                  const vals: Record<string, number> = { pawn: 1, knight: 3, bishop: 3, rook: 5, queen: 9 };
                  return bottomPlayerCapturedPieces.reduce((s, p) => s + (vals[p] ?? 0), 0);
                })()}</span>
              </div>
            </div>
          </div>
        )}



      </div>
    </div>
  );
};

export default ChessBoard;

