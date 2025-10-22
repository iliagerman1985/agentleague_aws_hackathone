/**
 * Help-themed background art
 * Displays question marks, lightbulbs, and info elements
 */

import React from "react";
import { cn } from "@/lib/utils";

interface HelpBackgroundProps {
  className?: string;
  opacity?: number;
}

export const HelpBackground: React.FC<HelpBackgroundProps> = ({
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
      {/* Help gradient overlays - warm, friendly colors */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-300/25 via-transparent to-orange-400/25" />
      <div className="absolute inset-0 bg-gradient-to-tr from-yellow-400/20 via-transparent to-amber-500/20" />

      {/* Large question mark - right side */}
      <svg
        className="absolute top-10 right-10 w-56 h-56 md:w-72 md:h-72 opacity-70"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="50" cy="50" r="40" fill="#f59e0b" opacity="0.3" />
        <path d="M35 35 Q35 25 45 25 Q55 25 55 35 Q55 45 50 50 L50 60" stroke="#d97706" strokeWidth="6" strokeLinecap="round" opacity="0.7" />
        <circle cx="50" cy="72" r="4" fill="#d97706" opacity="0.7" />
      </svg>

      {/* Lightbulb - bottom left */}
      <svg
        className="absolute bottom-12 left-10 w-28 h-36 opacity-75"
        viewBox="0 0 60 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Bulb */}
        <ellipse cx="30" cy="25" rx="18" ry="22" fill="#fbbf24" opacity="0.6" />
        <path d="M20 40 L20 50 Q20 55 25 55 L35 55 Q40 55 40 50 L40 40" fill="#f59e0b" opacity="0.5" />
        {/* Base */}
        <rect x="24" y="55" width="12" height="8" fill="#d97706" opacity="0.6" />
        <rect x="26" y="63" width="8" height="4" fill="#b45309" opacity="0.6" />
        {/* Light rays */}
        <line x1="10" y1="15" x2="5" y2="10" stroke="#fbbf24" strokeWidth="2" opacity="0.5" />
        <line x1="50" y1="15" x2="55" y2="10" stroke="#fbbf24" strokeWidth="2" opacity="0.5" />
        <line x1="8" y1="25" x2="2" y2="25" stroke="#fbbf24" strokeWidth="2" opacity="0.5" />
        <line x1="52" y1="25" x2="58" y2="25" stroke="#fbbf24" strokeWidth="2" opacity="0.5" />
      </svg>

      {/* Info icon - top left */}
      <svg
        className="absolute top-16 left-12 w-24 h-24 opacity-65"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="50" cy="50" r="35" fill="none" stroke="#f59e0b" strokeWidth="4" opacity="0.6" />
        <circle cx="50" cy="30" r="4" fill="#d97706" opacity="0.7" />
        <line x1="50" y1="42" x2="50" y2="70" stroke="#d97706" strokeWidth="5" strokeLinecap="round" opacity="0.7" />
      </svg>

      {/* Book icon - center */}
      <svg
        className="absolute top-1/3 left-1/3 w-32 h-32 opacity-55"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="20" y="25" width="60" height="50" rx="3" fill="#fbbf24" opacity="0.5" />
        <line x1="50" y1="25" x2="50" y2="75" stroke="#d97706" strokeWidth="2" opacity="0.6" />
        <line x1="30" y1="40" x2="45" y2="40" stroke="#d97706" strokeWidth="1.5" opacity="0.5" />
        <line x1="30" y1="50" x2="45" y2="50" stroke="#d97706" strokeWidth="1.5" opacity="0.5" />
        <line x1="55" y1="40" x2="70" y2="40" stroke="#d97706" strokeWidth="1.5" opacity="0.5" />
        <line x1="55" y1="50" x2="70" y2="50" stroke="#d97706" strokeWidth="1.5" opacity="0.5" />
      </svg>

      {/* Compass/navigation - bottom right */}
      <svg
        className="absolute bottom-20 right-1/4 w-24 h-24 opacity-60"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="50" cy="50" r="35" fill="none" stroke="#f59e0b" strokeWidth="3" opacity="0.5" />
        <polygon points="50,25 55,45 50,50 45,45" fill="#d97706" opacity="0.6" />
        <polygon points="50,75 45,55 50,50 55,55" fill="#fbbf24" opacity="0.5" />
        <circle cx="50" cy="50" r="4" fill="#d97706" opacity="0.7" />
      </svg>

      {/* Wave pattern */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="help-waves" x="0" y="0" width="100" height="40" patternUnits="userSpaceOnUse">
            <path d="M0,20 Q25,10 50,20 T100,20" fill="none" stroke="#f59e0b" strokeWidth="1" opacity="0.2" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#help-waves)" />
      </svg>

      {/* Sparkles and dots */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.5">
          <circle cx="150" cy="60" r="2" fill="#fbbf24" />
          <circle cx="280" cy="90" r="1.5" fill="#f59e0b" />
          <circle cx="420" cy="50" r="1.8" fill="#d97706" />
          <polygon points="550,70 552,76 558,76 553,80 555,86 550,82 545,86 547,80 542,76 548,76" fill="#fbbf24" transform="scale(0.5)" />
        </g>
      </svg>
    </div>
  );
};

export default HelpBackground;

