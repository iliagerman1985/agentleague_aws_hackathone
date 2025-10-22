import React from "react";

export const TinyDonut: React.FC<{ value: number; color?: string; className?: string }>
 = ({ value, color = "#A3E635", className }) => {
  const size = 48; const stroke = 6; const r = (size - stroke) / 2; const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  return (
    <svg width={size} height={size} className={className} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} stroke="#334155" strokeWidth={stroke} fill="none" />
      <circle cx={size/2} cy={size/2} r={r} stroke={color} strokeWidth={stroke} fill="none"
        strokeDasharray={c} strokeDashoffset={c - (pct/100)*c} strokeLinecap="round" transform={`rotate(-90 ${size/2} ${size/2})`} />
    </svg>
  );
};

