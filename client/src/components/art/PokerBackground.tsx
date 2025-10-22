/**
 * Poker-themed background art component
 * Displays subtle card suits and poker chip patterns
 */

import React from "react";
import { cn } from "@/lib/utils";

interface PokerBackgroundProps {
  className?: string;
  opacity?: number;
}

export const PokerBackground: React.FC<PokerBackgroundProps> = ({
  className,
  opacity = 0.03
}) => {
  return (
    <div
      className={cn("absolute inset-0 overflow-hidden pointer-events-none min-h-full", className)}
      style={{ opacity }}
    >
      {/* Rich gradient overlays: felt green and card red for bolder vibe (increased) */}
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-700/45 via-emerald-600/30 to-emerald-900/50" />
      <div className="absolute inset-0 bg-gradient-to-tr from-rose-600/28 via-transparent to-emerald-800/28" />

      {/* Full-height felt texture pattern with green tones */}
      <svg
        className="absolute inset-0 w-full h-full opacity-30"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <pattern id="felt-texture" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
            <circle cx="25" cy="25" r="1" fill="#059669" opacity="0.3" />
            <circle cx="75" cy="75" r="1" fill="#047857" opacity="0.25" />
            <circle cx="50" cy="50" r="1" fill="#10B981" opacity="0.2" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#felt-texture)" />
      </svg>

      {/* Spade symbol - black */}
      <svg
        className="absolute top-10 right-10 w-32 h-32 md:w-48 md:h-48 opacity-80"
        viewBox="0 0 24 24"
        fill="#1F2937"
      >
        <path d="M12 2C9.5 4.5 7 7 7 10c0 2.2 1.8 4 4 4 .4 0 .8-.1 1.2-.2-.1.4-.2.8-.2 1.2 0 1.1.9 2 2 2h-4c0 1.1.9 2 2 2h4c1.1 0 2-.9 2-2h-4c1.1 0 2-.9 2-2 0-.4-.1-.8-.2-1.2.4.1.8.2 1.2.2 2.2 0 4-1.8 4-4 0-3-2.5-5.5-5-8z" />
      </svg>

      {/* Heart symbol - red */}
      <svg
        className="absolute bottom-20 left-10 w-28 h-28 md:w-40 md:h-40 opacity-75"
        viewBox="0 0 24 24"
        fill="#DC2626"
      >
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
      </svg>

      {/* Diamond symbol - red */}
      <svg
        className="absolute top-1/3 left-1/4 w-24 h-24 md:w-36 md:h-36 opacity-70"
        viewBox="0 0 24 24"
        fill="#EF4444"
      >
        <path d="M12 2L2 12l10 10 10-10L12 2z" />
      </svg>

      {/* Club symbol - black */}
      <svg
        className="absolute bottom-1/4 right-1/4 w-26 h-26 md:w-38 md:h-38 opacity-75"
        viewBox="0 0 24 24"
        fill="#374151"
      >
        <path d="M12 2c-1.1 0-2 .9-2 2 0 .7.4 1.4 1 1.7-.3.1-.5.2-.8.3-1.5.7-2.5 2.2-2.5 3.9 0 2.2 1.8 4 4 4 .4 0 .8-.1 1.2-.2-.1.4-.2.8-.2 1.2 0 1.1.9 2 2 2h-4c0 1.1.9 2 2 2h4c1.1 0 2-.9 2-2h-4c1.1 0 2-.9 2-2 0-.4-.1-.8-.2-1.2.4.1.8.2 1.2.2 2.2 0 4-1.8 4-4 0-1.7-1-3.2-2.5-3.9-.3-.1-.5-.2-.8-.3.6-.3 1-1 1-1.7 0-1.1-.9-2-2-2z" />
      </svg>

      {/* Poker chip pattern - gold/yellow */}
      <svg
        className="absolute top-1/2 right-10 w-20 h-20 md:w-32 md:h-32 opacity-28"
        viewBox="0 0 100 100"
        fill="none"
        stroke="#F59E0B"
        strokeWidth="2"
      >
        <circle cx="50" cy="50" r="45" />
        <circle cx="50" cy="50" r="35" />
        <circle cx="50" cy="50" r="25" />
        <line x1="50" y1="5" x2="50" y2="20" />
        <line x1="50" y1="80" x2="50" y2="95" />
        <line x1="5" y1="50" x2="20" y2="50" />
        <line x1="80" y1="50" x2="95" y2="50" />
        <line x1="18" y1="18" x2="28" y2="28" />
        <line x1="72" y1="72" x2="82" y2="82" />
        <line x1="82" y1="18" x2="72" y2="28" />
        <line x1="28" y1="72" x2="18" y2="82" />
      </svg>

      {/* Card deck pattern - white/light gray */}
      <svg
        className="absolute bottom-10 right-1/3 w-16 h-16 md:w-24 md:h-24 opacity-36"
        viewBox="0 0 100 140"
        fill="none"
        stroke="#E5E7EB"
        strokeWidth="2"
      >
        <rect x="5" y="10" width="70" height="100" rx="5" fill="none" />
        <rect x="10" y="15" width="70" height="100" rx="5" fill="none" />
        <rect x="15" y="20" width="70" height="100" rx="5" fill="none" />
      </svg>
    </div>
  );
};

