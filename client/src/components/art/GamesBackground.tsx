/**
 * Games-themed background art
 * Displays game controller and gaming elements
 */

import React from "react";
import { cn } from "@/lib/utils";

interface GamesBackgroundProps {
  className?: string;
  opacity?: number;
}

export const GamesBackground: React.FC<GamesBackgroundProps> = ({
  className,
  opacity = 0.16,
}) => {
  return (
    <div
      className={cn(
        "absolute inset-0 overflow-hidden pointer-events-none min-h-full",
        className
      )}
      style={{ opacity }}
    >
      {/* Gaming gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/30 via-transparent to-blue-500/30" />
      <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/20 via-transparent to-purple-600/20" />

      {/* Large game controller - right side */}
      <svg
        className="absolute top-10 right-8 w-64 h-64 md:w-80 md:h-80 opacity-70"
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Controller body */}
        <ellipse cx="100" cy="100" rx="80" ry="50" fill="#6366f1" opacity="0.6" />
        <ellipse cx="100" cy="100" rx="70" ry="42" fill="#818cf8" opacity="0.4" />
        
        {/* D-pad left */}
        <rect x="50" y="95" width="20" height="10" rx="2" fill="#4f46e5" opacity="0.8" />
        <rect x="55" y="90" width="10" height="20" rx="2" fill="#4f46e5" opacity="0.8" />
        
        {/* Action buttons right */}
        <circle cx="140" cy="90" r="6" fill="#06b6d4" opacity="0.8" />
        <circle cx="155" cy="100" r="6" fill="#0891b2" opacity="0.8" />
        <circle cx="140" cy="110" r="6" fill="#14b8a6" opacity="0.8" />
        <circle cx="125" cy="100" r="6" fill="#0ea5e9" opacity="0.8" />
      </svg>

      {/* Dice - bottom left */}
      <svg
        className="absolute bottom-12 left-10 w-24 h-24 opacity-75"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="10" y="10" width="80" height="80" rx="8" fill="#6366f1" opacity="0.7" />
        <circle cx="30" cy="30" r="5" fill="#fff" />
        <circle cx="50" cy="50" r="5" fill="#fff" />
        <circle cx="70" cy="70" r="5" fill="#fff" />
        <circle cx="30" cy="70" r="5" fill="#fff" />
        <circle cx="70" cy="30" r="5" fill="#fff" />
      </svg>

      {/* Playing card - top left */}
      <svg
        className="absolute top-16 left-12 w-20 h-28 opacity-65"
        viewBox="0 0 60 84"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="2" y="2" width="56" height="80" rx="4" fill="#fff" opacity="0.9" />
        <text x="10" y="20" fontSize="16" fontWeight="bold" fill="#ef4444">A</text>
        <path d="M30 35 L35 45 L25 45 Z" fill="#ef4444" />
      </svg>

      {/* Chess knight silhouette - center */}
      <svg
        className="absolute top-1/3 left-1/3 w-32 h-32 opacity-50"
        viewBox="0 0 100 100"
        fill="#0891b2"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M30 90 L70 90 L65 70 Q60 60 55 50 Q52 45 50 35 Q48 30 45 25 L40 30 Q35 25 30 30 L28 40 Q25 50 30 60 Z" opacity="0.6" />
      </svg>

      {/* Pixel art elements */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="pixel-grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <rect x="0" y="0" width="8" height="8" fill="#6366f1" opacity="0.15" />
            <rect x="10" y="10" width="8" height="8" fill="#0891b2" opacity="0.15" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#pixel-grid)" />
      </svg>

      {/* Sparkle effects */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.5">
          <circle cx="150" cy="40" r="2" fill="#6366f1" />
          <circle cx="280" cy="70" r="1.5" fill="#0891b2" />
          <circle cx="420" cy="50" r="1.8" fill="#14b8a6" />
          <polygon points="600,60 602,66 608,66 603,70 605,76 600,72 595,76 597,70 592,66 598,66" fill="#818cf8" transform="scale(0.4)" />
        </g>
      </svg>
    </div>
  );
};

export default GamesBackground;

