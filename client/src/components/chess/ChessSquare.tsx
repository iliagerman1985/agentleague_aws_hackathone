import React from 'react';

interface ChessSquareProps {
  coord: string; // e.g., "e4"
  isLight: boolean;
  selected?: boolean;
  isMoveTarget?: boolean;
  isLastFrom?: boolean;
  isLastTo?: boolean;
  onClick?: () => void;
  children?: React.ReactNode;
}

export const ChessSquare: React.FC<ChessSquareProps> = ({ coord, isLight, selected, isMoveTarget, isLastFrom, isLastTo, onClick, children }) => {
  // Fixed board colors regardless of theme (lichess-like)
  const bg = isLight ? '#EEEED2' : '#769656';
  const sel = selected ? 'outline outline-2 outline-brand-teal' : '';
  const tgt = '';
  // Hover/focus visuals disabled per request (no animations/outline changes on squares)

  return (
    <button
      type="button"
      data-coord={coord}
      onClick={onClick}
      className={`relative w-full h-full ${sel} ${tgt} grid place-items-center no-card-hover focus:outline-none focus:ring-0`}
      style={{ backgroundColor: bg }}
      aria-label={`Square ${coord}`}
      aria-pressed={selected ? true : undefined}
    >
      {isLastFrom && <span className="chess-last" aria-hidden />}
      {isLastTo && <span className="chess-last-to" aria-hidden />}
      {isMoveTarget && <span className={`chess-dot ${children ? 'capture' : ''}`} />}
      {children}
    </button>
  );
};

export default ChessSquare;

