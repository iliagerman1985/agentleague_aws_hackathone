/**
 * Tools-themed background art
 * Displays wrench, gear, and tool elements
 */

import React from "react";
import { cn } from "@/lib/utils";

interface ToolsBackgroundProps {
  className?: string;
  opacity?: number;
}

export const ToolsBackground: React.FC<ToolsBackgroundProps> = ({
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
      {/* Industrial gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-400/25 via-transparent to-zinc-500/25" />
      <div className="absolute inset-0 bg-gradient-to-tr from-gray-500/20 via-transparent to-slate-600/20" />

      {/* Large gear - right side */}
      <svg
        className="absolute top-10 right-8 w-56 h-56 md:w-72 md:h-72 opacity-70"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="50" cy="50" r="30" fill="#64748b" opacity="0.5" />
        <circle cx="50" cy="50" r="20" fill="none" stroke="#475569" strokeWidth="3" opacity="0.6" />
        {/* Gear teeth */}
        <rect x="48" y="10" width="4" height="10" fill="#64748b" opacity="0.7" />
        <rect x="48" y="80" width="4" height="10" fill="#64748b" opacity="0.7" />
        <rect x="10" y="48" width="10" height="4" fill="#64748b" opacity="0.7" />
        <rect x="80" y="48" width="10" height="4" fill="#64748b" opacity="0.7" />
        <rect x="20" y="20" width="4" height="10" fill="#64748b" opacity="0.7" transform="rotate(45 22 25)" />
        <rect x="76" y="20" width="4" height="10" fill="#64748b" opacity="0.7" transform="rotate(-45 78 25)" />
        <rect x="20" y="76" width="4" height="10" fill="#64748b" opacity="0.7" transform="rotate(-45 22 81)" />
        <rect x="76" y="76" width="4" height="10" fill="#64748b" opacity="0.7" transform="rotate(45 78 81)" />
      </svg>

      {/* Wrench - bottom left */}
      <svg
        className="absolute bottom-12 left-10 w-32 h-32 opacity-75"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M20 80 L30 70 L40 80 L30 90 Z" fill="#71717a" opacity="0.7" />
        <rect x="28" y="30" width="8" height="45" rx="2" fill="#52525b" opacity="0.7" transform="rotate(-45 32 52.5)" />
        <circle cx="60" cy="40" r="12" fill="none" stroke="#71717a" strokeWidth="4" opacity="0.6" />
        <path d="M68 32 L80 20 L85 25 L73 37" fill="#52525b" opacity="0.7" />
      </svg>

      {/* Hammer - top left */}
      <svg
        className="absolute top-16 left-12 w-28 h-28 opacity-65"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="40" y="60" width="6" height="35" rx="2" fill="#52525b" opacity="0.7" />
        <rect x="25" y="45" width="36" height="18" rx="3" fill="#71717a" opacity="0.7" />
      </svg>

      {/* Small gear - center */}
      <svg
        className="absolute top-1/3 left-1/3 w-24 h-24 opacity-55"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="50" cy="50" r="20" fill="#64748b" opacity="0.5" />
        <circle cx="50" cy="50" r="12" fill="none" stroke="#475569" strokeWidth="2" opacity="0.6" />
        <rect x="48" y="20" width="4" height="8" fill="#64748b" opacity="0.7" />
        <rect x="48" y="72" width="4" height="8" fill="#64748b" opacity="0.7" />
        <rect x="20" y="48" width="8" height="4" fill="#64748b" opacity="0.7" />
        <rect x="72" y="48" width="8" height="4" fill="#64748b" opacity="0.7" />
      </svg>

      {/* Screwdriver - bottom right */}
      <svg
        className="absolute bottom-20 right-1/4 w-20 h-20 opacity-60"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="45" y="60" width="10" height="30" rx="2" fill="#f59e0b" opacity="0.6" />
        <rect x="47" y="30" width="6" height="32" rx="1" fill="#52525b" opacity="0.7" />
        <polygon points="50,20 45,30 55,30" fill="#71717a" opacity="0.7" />
      </svg>

      {/* Grid pattern */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="tool-grid" x="0" y="0" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#64748b" strokeWidth="1" opacity="0.2" />
            <circle cx="0" cy="0" r="1.5" fill="#71717a" opacity="0.3" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#tool-grid)" />
      </svg>

      {/* Bolt/nut icons scattered */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.5">
          <circle cx="150" cy="50" r="6" fill="none" stroke="#64748b" strokeWidth="2" />
          <circle cx="150" cy="50" r="3" fill="#71717a" />
          
          <circle cx="300" cy="120" r="5" fill="none" stroke="#64748b" strokeWidth="1.5" />
          <circle cx="300" cy="120" r="2.5" fill="#71717a" />
          
          <circle cx="480" cy="80" r="4" fill="none" stroke="#64748b" strokeWidth="1.5" />
          <circle cx="480" cy="80" r="2" fill="#71717a" />
        </g>
      </svg>
    </div>
  );
};

export default ToolsBackground;

