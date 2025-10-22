import React from 'react';
import type { Color, PieceType } from '@/types/chess';

interface CapturedPiecesProps {
  capturedByWhite: PieceType[];
  capturedByBlack: PieceType[];
  materialAdvantage: number;
  layout?: 'horizontal' | 'vertical';
  side?: 'white' | 'black';
  rows?: 'both' | 'white' | 'black';
  whiteLabel?: string;
  blackLabel?: string;
}

// Unicode symbols for pieces - using filled symbols matching the board
const pieceSymbols: Record<PieceType, string> = {
  king: '♚',
  queen: '♛',
  rook: '♜',
  bishop: '♝',
  knight: '♞',
  pawn: '♟',
};

// Colors matching ChessPieceView component
const getPieceStyle = (color: 'white' | 'black') => {
  const fill = color === 'white' ? '#F0F2F5' : '#111827';
  const stroke = color === 'white' ? 'rgba(17,24,39,0.8)' : 'rgba(255,255,255,0.25)';
  const filter = color === 'white'
    ? 'drop-shadow(0 0 2px rgba(0,0,0,0.35))'
    : 'drop-shadow(0 0 1px rgba(255,255,255,0.25))';
  const outline = color === 'white'
    ? '-1px 0 #111827, 1px 0 #111827, 0 -1px #111827, 0 1px #111827, -1px -1px #111827, 1px -1px #111827, -1px 1px #111827, 1px 1px #111827'
    : undefined;

  return { fill, stroke, filter, outline };
};

// Piece values for sorting
const pieceOrder: Record<PieceType, number> = {
  queen: 1,
  rook: 2,
  bishop: 3,
  knight: 4,
  pawn: 5,
  king: 6,
};

const CapturedPiecesList: React.FC<{ pieces: PieceType[]; displayColor: Color; capturedBy: string }> = ({ pieces, displayColor, capturedBy }) => {
  // Handle undefined/null pieces array
  if (!pieces || !Array.isArray(pieces)) {
    pieces = [];
  }

  // Sort pieces by value (queen, rook, bishop, knight, pawn)
  const sortedPieces = [...pieces].sort((a, b) => pieceOrder[a] - pieceOrder[b]);

  // Debug logging
  console.log('[CapturedPiecesList]', { capturedBy, displayColor, pieces: sortedPieces });

  return (
    <div className="flex items-center gap-2 min-h-[22px]">
      <div className="flex flex-wrap gap-1 items-center flex-1">
        {sortedPieces.length === 0 ? (
          <span className="text-slate-400 dark:text-slate-600 text-[10px] italic">—</span>
        ) : (
          sortedPieces.map((pieceType, idx) => {
            const pieceSymbol = pieceSymbols[pieceType];
            const style = getPieceStyle(displayColor);
            if (pieceType === 'pawn') {
              return (
                <span key={idx} className="inline-flex leading-none select-none" style={{ filter: style.filter }}>
                  <svg width="1.55em" height="1.55em" viewBox="0 0 45 45" aria-hidden>
                    <g fill={style.fill} stroke={style.stroke} strokeWidth="1.1">
                      <circle cx="22.5" cy="12" r="5" />
                      <path d="M 17 25 C 12 25, 10 32, 10 36 L 35 36 C 35 32, 33 25, 28 25" />
                      <rect x="12" y="36" width="23" height="4" rx="1.5" />
                    </g>
                  </svg>
                </span>
              );
            }
            return (
              <span
                key={idx}
                className="inline-flex leading-none select-none"
                style={{ color: style.fill, filter: style.filter, textShadow: style.outline }}
              >
                <span className="text-[1.55em] leading-none" style={{ color: style.fill }}>{pieceSymbol}</span>
              </span>
            );
          })
        )}
      </div>
    </div>
  );
};

export const CapturedPieces: React.FC<CapturedPiecesProps> = ({
  capturedByWhite,
  capturedByBlack,
  materialAdvantage,
  layout = 'horizontal',
  side,
  rows = 'both',
  whiteLabel,
  blackLabel,
}) => {
  // Determine which side has the advantage
  const whiteAdvantage = materialAdvantage > 0 ? materialAdvantage : 0;
  const blackAdvantage = materialAdvantage < 0 ? Math.abs(materialAdvantage) : 0;

  // Vertical layout for side panels
  if (layout === 'vertical' && side) {
    const pieces = side === 'black' ? capturedByWhite : capturedByBlack;
    const displayColor = side === 'black' ? 'black' : 'white';
    const advantage = side === 'white' ? blackAdvantage : whiteAdvantage;

    // Sort pieces by value
    const sortedPieces = [...pieces].sort((a, b) => pieceOrder[a] - pieceOrder[b]);

    return (
      <div className="flex flex-col items-center gap-2 min-w-[60px] md:min-w-[80px] h-full">
        {/* Material advantage badge */}
        {advantage > 0 && (
          <div className="px-2 py-1 rounded-md bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs font-bold">
            +{advantage}
          </div>
        )}

        {/* Captured pieces - vertical stack - only show if there are pieces */}
        {sortedPieces.length > 0 && (
          <div
            className={`flex flex-col items-center gap-1 flex-1 overflow-y-auto max-h-[500px] w-full rounded-md border px-2 py-2
              ${displayColor === 'black' ? 'bg-slate-100/75 dark:bg-slate-700/55 border-slate-300/70 dark:border-slate-600/70'
                                         : 'bg-slate-300/70 dark:bg-slate-900/55 border-slate-400/70 dark:border-slate-700/70'}`}
          >
            {sortedPieces.map((pieceType, idx) => {
              const style = getPieceStyle(displayColor);
              if (pieceType === 'pawn') {
                return (
                  <span key={idx} className="inline-flex leading-none select-none" style={{ filter: style.filter }}>
                    <svg width="2.3em" height="2.3em" viewBox="0 0 45 45" aria-hidden>
                      <g fill={style.fill} stroke={style.stroke} strokeWidth="1.2">
                        <circle cx="22.5" cy="12" r="5" />
                        <path d="M 17 25 C 12 25, 10 32, 10 36 L 35 36 C 35 32, 33 25, 28 25" />
                        <rect x="12" y="36" width="23" height="4" rx="1.5" />
                      </g>
                    </svg>
                  </span>
                );
              } else {
                return (
                  <span
                    key={idx}
                    className="inline-flex leading-none select-none"
                    style={{ color: style.fill, filter: style.filter, textShadow: style.outline }}
                  >
                    <span className="text-[2.3em] md:text-[2.5em] leading-none" style={{ color: style.fill }}>{pieceSymbols[pieceType]}</span>
                  </span>
                );
              }
            })}
          </div>
        )}
      </div>
    );
  }

  // Horizontal layout (compact, with optional labels below each row)
  return (
    <div className="w-full rounded-lg p-1.5 md:p-2 border border-slate-200/70 dark:border-slate-700/70 bg-slate-50/60 dark:bg-slate-900/50 space-y-1">
      {(rows === 'both' || rows === 'white') && (
        <div className="space-y-0.5">
          <div className={`flex items-center gap-1 p-1 rounded-md ${whiteAdvantage > 0 ? 'ring-1 ring-slate-300/70 dark:ring-slate-600/70' : ''}`}>
            <CapturedPiecesList pieces={capturedByWhite} displayColor="black" capturedBy="white" />
            {whiteAdvantage > 0 && (
              <div className="ml-auto px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-[10px] font-bold">
                +{whiteAdvantage}
              </div>
            )}
          </div>
          {whiteLabel && (
            <div className="text-[10px] text-center text-muted-foreground uppercase tracking-wide">{whiteLabel}</div>
          )}
        </div>
      )}

      {(rows === 'both' || rows === 'black') && (
        <div className="space-y-0.5">
          <div className={`flex items-center gap-1 p-1 rounded-md ${blackAdvantage > 0 ? 'ring-1 ring-slate-300/70 dark:ring-slate-600/70' : ''}`}>
            <CapturedPiecesList pieces={capturedByBlack} displayColor="white" capturedBy="black" />
            {blackAdvantage > 0 && (
              <div className="ml-auto px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-[10px] font-bold">
                +{blackAdvantage}
              </div>
            )}
          </div>
          {blackLabel && (
            <div className="text-[10px] text-center text-muted-foreground uppercase tracking-wide">{blackLabel}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default CapturedPieces;

