/**
 * Podium-themed background art for Leaderboard pages
 */

import React from "react";
import { cn } from "@/lib/utils";

interface TrophiesBackgroundProps {
  className?: string;
  opacity?: number;
}

export const TrophiesBackground: React.FC<TrophiesBackgroundProps> = ({
  className,
  opacity = 0.12,
}) => {
  return (
    <div
      className={cn(
        "absolute inset-0 overflow-hidden pointer-events-none min-h-full",
        className
      )}
      style={{ opacity }}
    >
      {/* soft glow bands - gold/amber theme */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-200/40 via-transparent to-amber-300/40" />
      <div className="absolute inset-0 bg-gradient-to-tr from-amber-400/25 via-transparent to-yellow-300/25" />

      {/* Large podium structure - right side */}
      <svg
        className="absolute bottom-0 right-10 w-64 h-64 md:w-80 md:h-80 opacity-75"
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* 1st place - tallest (center) */}
        <rect x="70" y="60" width="60" height="140" fill="#fbbf24" opacity="0.8" />
        <text x="100" y="130" fontSize="32" fontWeight="bold" fill="#78350f" textAnchor="middle">1</text>

        {/* 2nd place - medium (left) */}
        <rect x="10" y="100" width="55" height="100" fill="#d4d4d8" opacity="0.7" />
        <text x="37.5" y="150" fontSize="28" fontWeight="bold" fill="#3f3f46" textAnchor="middle">2</text>

        {/* 3rd place - shortest (right) */}
        <rect x="135" y="130" width="55" height="70" fill="#d97706" opacity="0.6" />
        <text x="162.5" y="165" fontSize="24" fontWeight="bold" fill="#78350f" textAnchor="middle">3</text>
      </svg>

      {/* Small podium - left side */}
      <svg
        className="absolute bottom-10 left-8 w-32 h-32 opacity-60"
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="40" y="40" width="40" height="80" fill="#fbbf24" opacity="0.7" />
        <rect x="5" y="70" width="30" height="50" fill="#d4d4d8" opacity="0.6" />
        <rect x="85" y="85" width="30" height="35" fill="#d97706" opacity="0.5" />
      </svg>

      {/* Trophy icon top-left */}
      <svg
        className="absolute top-8 left-12 w-24 h-24 opacity-70"
        viewBox="0 0 64 64"
        fill="#f59e0b"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M48 8h-6V4H22v4h-6v6c0 6.6 5.4 12 12 12h8c6.6 0 12-5.4 12-12V8Z" opacity=".8" />
        <rect x="28" y="32" width="8" height="10" rx="1" />
        <rect x="22" y="44" width="20" height="4" rx="1" />
      </svg>

      {/* Stars/sparkles for winners */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.6" fill="#fbbf24">
          <polygon points="30,20 32,26 38,26 33,30 35,36 30,32 25,36 27,30 22,26 28,26" />
          <polygon points="160,40 161,44 165,44 162,46 163,50 160,48 157,50 158,46 155,44 159,44" transform="scale(0.7)" />
          <polygon points="420,60 422,66 428,66 423,70 425,76 420,72 415,76 417,70 412,66 418,66" transform="scale(0.5)" />
        </g>
      </svg>

      {/* Confetti particles */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.5">
          <circle cx="80" cy="30" r="2" fill="#f59e0b" />
          <circle cx="200" cy="50" r="1.5" fill="#fbbf24" />
          <circle cx="350" cy="70" r="1.8" fill="#d97706" />
          <rect x="500" y="40" width="3" height="3" fill="#fbbf24" transform="rotate(45 501.5 41.5)" />
          <rect x="650" y="80" width="2.5" height="2.5" fill="#f59e0b" transform="rotate(30 651.25 81.25)" />
        </g>
      </svg>
    </div>
  );
};

export default TrophiesBackground;

