import React from 'react';
import type { ChessPiece } from '@/types/chess';

// Filled glyphs for non-pawn pieces (unicode renders reliably)
const filledGlyphs: Record<string, string> = {
  rook: '♜', knight: '♞', bishop: '♝', queen: '♛', king: '♚',
};

const PawnSvg: React.FC<{ fill: string; stroke: string }> = ({ fill, stroke }) => (
  <svg viewBox="0 0 45 45" width="1em" height="1em" aria-hidden>
    <g fill={fill} stroke={stroke} strokeWidth="1.2">
      <circle cx="22.5" cy="14" r="5.2" />
      <path d="M22.5 20.8c-5.5 0-9.5 3.2-9.5 7.4 0 2 1 3.8 2.7 5.2h13.6c1.7-1.4 2.7-3.2 2.7-5.2 0-4.2-4-7.4-9.5-7.4z" />
      <rect x="13" y="33" width="19" height="3.2" rx="1.2" />
      <rect x="11" y="36.8" width="23" height="3.2" rx="1.2" />
    </g>
  </svg>
);


export const ChessPieceView: React.FC<{ piece: ChessPiece }> = ({ piece }) => {
  // Visual tuning: consistent sizes and slight per-piece scaling so pawns aren't oversized
  const baseFont = 'clamp(18px, 7vmin, 50px)';
  const scaleByType: Record<string, number> = {
    pawn: 0.84,
    rook: 1.04,
    bishop: 1.04,
    knight: 1.06,
    queen: 1.10,
    king: 1.10,
  };
  const scale = scaleByType[piece.type] ?? 1.04;

  // Colors close to your reference (fixed, theme-independent)
  const fill = piece.color === 'white' ? '#F0F2F5' : '#111827';
  const stroke = piece.color === 'white' ? 'rgba(17,24,39,0.8)' : 'rgba(255,255,255,0.25)';
  const filter = piece.color === 'white'
    ? 'drop-shadow(0 0 2px rgba(0,0,0,0.35))'
    : 'drop-shadow(0 0 1px rgba(255,255,255,0.25))';
  const outline = piece.color === 'white' && piece.type !== 'pawn'
    ? '-1px 0 #111827, 1px 0 #111827, 0 -1px #111827, 0 1px #111827, -1px -1px #111827, 1px -1px #111827, -1px 1px #111827, 1px 1px #111827'
    : undefined;


  if (piece.type === 'pawn') {
    return (
      <span className="select-none leading-none chess-piece" style={{ fontSize: baseFont, transform: `scale(${scale})`, filter }}>
        <PawnSvg fill={fill} stroke={stroke} />
      </span>
    );
  }

  const glyph = filledGlyphs[piece.type] ?? '?';
  return (
    <span className="select-none leading-none chess-piece" style={{ color: fill, fontSize: baseFont, transform: `scale(${scale})`, filter, textShadow: outline }}>
      {glyph}
    </span>
  );
};

export default ChessPieceView;

