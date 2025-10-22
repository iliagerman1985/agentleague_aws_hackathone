import React from "react";

// Minimal sparkline-style area using inline SVG (no extra deps)
export const TinyArea: React.FC<{ points: number[]; color?: string; className?: string }>
  = ({ points, color = "#34D399", className }) => {
  const w = 160; const h = 48;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const sx = (i: number) => (i / (points.length - 1)) * (w - 2) + 1;
  const sy = (v: number) => h - ((v - min) / Math.max(1, max - min)) * (h - 6) - 3;
  const path = points.map((v, i) => `${i === 0 ? "M" : "L"}${sx(i)},${sy(v)}`).join(" ");
  const area = `${path} L${w-1},${h-3} L1,${h-3} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className={className}>
      <path d={area} fill={`${color}22`} />
      <path d={path} stroke={color} strokeWidth={2} fill="none" />
    </svg>
  );
};

