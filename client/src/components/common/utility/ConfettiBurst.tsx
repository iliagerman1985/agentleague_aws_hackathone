import React, { useMemo } from "react";

interface ConfettiBurstProps {
  pieces?: number;
  durationMs?: number; // total fall duration per piece (randomized around this)
}

// Lightweight, dependency-free confetti burst for success moments
export const ConfettiBurst: React.FC<ConfettiBurstProps> = ({ pieces = 120, durationMs = 2200 }) => {
  const confetti = useMemo(() => {
    const colors = [
      "#22d3ee", // brand teal-ish
      "#10b981", // emerald
      "#f59e0b", // amber
      "#ef4444", // red
      "#8b5cf6", // violet
      "#06b6d4", // cyan
      "#84cc16", // lime
    ];
    return Array.from({ length: pieces }).map((_, i) => {
      const left = Math.random() * 100; // vw%
      const size = 6 + Math.random() * 8; // px
      const rotate = Math.random() * 360;
      const fall = durationMs * (0.8 + Math.random() * 0.5); // ms
      const delay = Math.random() * 200; // ms
      const color = colors[i % colors.length];
      const spin = 600 + Math.random() * 1000; // ms
      const opacity = 0.85;
      return { left, size, rotate, fall, delay, color, spin, opacity };
    });
  }, [pieces, durationMs]);

  return (
    <div className="pointer-events-none fixed inset-0 z-[9999] overflow-hidden">
      <style>{`
        @keyframes confetti-fall { to { transform: translate3d(0, 110vh, 0); opacity: 0.95; } }
        @keyframes confetti-rotate { to { transform: rotate(360deg); } }
      `}</style>
      {confetti.map((p, idx) => (
        <span
          key={idx}
          style={{
            position: "absolute",
            left: `${p.left}vw`,
            top: "-10vh",
            width: `${p.size}px`,
            height: `${p.size * 0.6}px`,
            borderRadius: 2,
            animation: `confetti-fall ${p.fall}ms linear ${p.delay}ms forwards`,
          }}
        >
          <span
            style={{
              display: "block",
              width: "100%",
              height: "100%",
              backgroundColor: p.color,
              opacity: p.opacity,
              transform: `rotate(${p.rotate}deg)`,
              boxShadow: "0 0 8px rgba(0,0,0,0.15)",
              animation: `confetti-rotate ${p.spin}ms linear ${p.delay}ms infinite`,
            }}
          />
        </span>
      ))}
    </div>
  );
};

export default ConfettiBurst;

