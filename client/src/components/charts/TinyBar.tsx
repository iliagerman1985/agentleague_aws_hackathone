import React from "react";

export const TinyBar: React.FC<{ values: number[]; color?: string; className?: string }>
 = ({ values, color = "#22D3EE", className }) => {
  const w = 160; const h = 48; const gap = 2;
  const bw = (w - gap * (values.length + 1)) / values.length;
  const max = Math.max(...values, 1);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className={className}>
      {values.map((v, i) => {
        const x = gap + i * (bw + gap);
        const bh = (v / max) * (h - 6);
        return <rect key={i} x={x} y={h - 3 - bh} width={bw} height={bh} fill={`${color}99`} rx={2} />
      })}
    </svg>
  );
};

