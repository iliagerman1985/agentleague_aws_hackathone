import React, { useState, useEffect } from 'react';
import type { ChessStateView, ChessPiece, PieceType, Color } from '@/types/chess';
import { ChessPieceView } from './ChessPiece';
import { ChessSquare } from './ChessSquare';
import { CapturedPieces } from './CapturedPieces';

function idxToSquare(r: number, c: number): string {
  return String.fromCharCode(97 + c) + String(8 - r);
}

function squareToIdx(square: string): { r: number; c: number } {
  const file = square.charCodeAt(0) - 97; // a=0
  const rank = parseInt(square[1]!, 10);
  return { r: 8 - rank, c: file };
}

export interface EditableChessBoardProps {
  state: ChessStateView;
  onStateChange: (newState: ChessStateView) => void;
}

export const EditableChessBoard: React.FC<EditableChessBoardProps> = ({ state, onStateChange }) => {
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [draggedPiece, setDraggedPiece] = useState<{ piece: ChessPiece; fromSquare: string } | null>(null);

  // Calculate captured pieces whenever board changes
  useEffect(() => {
    const calculateCapturedPieces = () => {
      // Starting material count for each piece type
      const startingCounts: Record<PieceType, number> = {
        pawn: 8,
        rook: 2,
        knight: 2,
        bishop: 2,
        queen: 1,
        king: 1,
      };

      // Piece values for material calculation
      const pieceValues: Record<PieceType, number> = {
        pawn: 1,
        knight: 3,
        bishop: 3,
        rook: 5,
        queen: 9,
        king: 0,
      };

      // Count current pieces on board
      const whiteCounts: Record<PieceType, number> = {
        pawn: 0,
        rook: 0,
        knight: 0,
        bishop: 0,
        queen: 0,
        king: 0,
      };
      const blackCounts: Record<PieceType, number> = {
        pawn: 0,
        rook: 0,
        knight: 0,
        bishop: 0,
        queen: 0,
        king: 0,
      };

      for (const rank of state.board) {
        for (const piece of rank) {
          if (piece) {
            if (piece.color === 'white') {
              whiteCounts[piece.type]++;
            } else {
              blackCounts[piece.type]++;
            }
          }
        }
      }

      // Calculate captured pieces
      const whiteCaptured: PieceType[] = [];
      const blackCaptured: PieceType[] = [];

      for (const pieceType of Object.keys(startingCounts) as PieceType[]) {
        const blackMissing = startingCounts[pieceType] - blackCounts[pieceType];
        for (let i = 0; i < blackMissing; i++) {
          whiteCaptured.push(pieceType);
        }

        const whiteMissing = startingCounts[pieceType] - whiteCounts[pieceType];
        for (let i = 0; i < whiteMissing; i++) {
          blackCaptured.push(pieceType);
        }
      }

      // Calculate material advantage
      let whiteMaterial = 0;
      let blackMaterial = 0;
      for (const pieceType of Object.keys(pieceValues) as PieceType[]) {
        whiteMaterial += pieceValues[pieceType] * whiteCounts[pieceType];
        blackMaterial += pieceValues[pieceType] * blackCounts[pieceType];
      }
      const materialAdvantage = whiteMaterial - blackMaterial;

      // Update state if values changed
      const capturedPieces: Record<Color, PieceType[]> = {
        white: whiteCaptured,
        black: blackCaptured,
      };

      if (
        JSON.stringify(state.capturedPieces) !== JSON.stringify(capturedPieces) ||
        state.materialAdvantage !== materialAdvantage
      ) {
        onStateChange({
          ...state,
          capturedPieces,
          materialAdvantage,
        });
      }
    };

    calculateCapturedPieces();
  }, [state.board]); // Only recalculate when board changes

  const handleSquareClick = (coord: string) => {
    const { r, c } = squareToIdx(coord);
    const piece = state.board[r]?.[c] ?? null;

    if (!selectedSquare) {
      // First click - select a piece
      if (piece) {
        setSelectedSquare(coord);
      }
      return;
    }

    // Second click - move piece or deselect
    if (coord === selectedSquare) {
      // Clicking same square - deselect
      setSelectedSquare(null);
      return;
    }

    // Move piece from selectedSquare to coord
    movePiece(selectedSquare, coord);
    setSelectedSquare(null);
  };

  const movePiece = (fromSquare: string, toSquare: string) => {
    const fromIdx = squareToIdx(fromSquare);
    const toIdx = squareToIdx(toSquare);
    
    const piece = state.board[fromIdx.r]?.[fromIdx.c];
    if (!piece) return;

    // Create new board with the move
    const newBoard = state.board.map(row => [...row]);
    newBoard[fromIdx.r][fromIdx.c] = null;
    newBoard[toIdx.r][toIdx.c] = piece;

    // Update state
    onStateChange({
      ...state,
      board: newBoard,
    });
  };

  const handleDragStart = (e: React.DragEvent, coord: string) => {
    const { r, c } = squareToIdx(coord);
    const piece = state.board[r]?.[c];
    if (piece) {
      setDraggedPiece({ piece, fromSquare: coord });
      e.dataTransfer.effectAllowed = 'move';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, coord: string) => {
    e.preventDefault();
    if (draggedPiece) {
      movePiece(draggedPiece.fromSquare, coord);
      setDraggedPiece(null);
    }
  };

  return (
    <div className="w-full max-w-[min(100vw,90vh,900px)] mx-auto px-2 md:px-4">
      <div className="flex gap-2 md:gap-4 items-center justify-center">
        {/* Left side - Black captured pieces (captured by White) */}
        <CapturedPieces
          capturedByWhite={state.capturedPieces?.white ?? []}
          capturedByBlack={[]}
          materialAdvantage={state.materialAdvantage ?? 0}
          layout="vertical"
          side="black"
        />

        {/* Chess board */}
        <div className="w-full aspect-square max-w-[min(70vw,70vh,600px)]">
          <div className="relative w-full h-full">
            <div className="absolute top-0 right-0 bottom-5 left-5 grid grid-cols-8 rounded-xl overflow-hidden border border-brand-teal/60 shadow-sm bg-white/40 dark:bg-white/5 backdrop-blur-sm">
            {state.board.map((row, r) =>
              row.map((cell, c) => {
                const coord = idxToSquare(r, c);
                const isLight = (r + c) % 2 === 0;
                const isSelected = selectedSquare === coord;
                const isDragging = draggedPiece?.fromSquare === coord;

                return (
                  <div
                    key={coord}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDrop(e, coord)}
                    className="relative w-full aspect-square"
                  >
                    <ChessSquare
                      coord={coord}
                      isLight={isLight}
                      selected={isSelected}
                      isMoveTarget={false}
                      isLastFrom={false}
                      isLastTo={false}
                      onClick={() => handleSquareClick(coord)}
                    >
                      {cell && (
                        <div
                          draggable
                          onDragStart={(e) => handleDragStart(e, coord)}
                          className={`cursor-move ${isDragging ? 'opacity-50' : ''}`}
                        >
                          <ChessPieceView piece={cell} />
                        </div>
                      )}
                    </ChessSquare>
                  </div>
                );
              })
            )}
          </div>
          {/* File labels (a–h) below within reserved gutter */}
          <div className="pointer-events-none absolute bottom-0 left-5 right-0 grid grid-cols-8 text-[8px] sm:text-[10px] md:text-xs font-medium text-gray-700/80 dark:text-gray-200/80">
            {Array.from({ length: 8 }, (_, i) => String.fromCharCode(97 + i)).map((f) => (
              <span key={f} className="text-center">{f}</span>
            ))}
          </div>
          {/* Rank labels (8–1) on left within reserved gutter */}
          <div className="pointer-events-none absolute top-0 bottom-5 left-0 w-5 flex flex-col text-[8px] sm:text-[10px] md:text-xs font-medium text-gray-700/80 dark:text-gray-200/80">
            {Array.from({ length: 8 }, (_, i) => 8 - i).map((rank) => (
              <span key={rank} className="flex-1 flex items-center justify-center">{rank}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - White captured pieces (captured by Black) */}
      <CapturedPieces
        capturedByWhite={[]}
        capturedByBlack={state.capturedPieces?.black ?? []}
        materialAdvantage={state.materialAdvantage ?? 0}
        layout="vertical"
        side="white"
      />
    </div>
    </div>
  );
};

export default EditableChessBoard;

