/**
 * Agents-themed background art
 * Displays AI/robot and neural network elements
 */

import React from "react";
import { cn } from "@/lib/utils";

interface AgentsBackgroundProps {
  className?: string;
  opacity?: number;
}

export const AgentsBackground: React.FC<AgentsBackgroundProps> = ({
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
      {/* AI gradient overlays - tech blue/purple theme */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/25 via-transparent to-purple-500/25" />
      <div className="absolute inset-0 bg-gradient-to-tr from-cyan-400/20 via-transparent to-indigo-500/20" />

      {/* Robot head silhouette - right side */}
      <svg
        className="absolute top-8 right-10 w-48 h-48 md:w-64 md:h-64 opacity-70"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Head */}
        <rect x="25" y="30" width="50" height="50" rx="8" fill="#3b82f6" opacity="0.6" />
        {/* Antenna */}
        <line x1="50" y1="20" x2="50" y2="30" stroke="#06b6d4" strokeWidth="2" opacity="0.7" />
        <circle cx="50" cy="18" r="3" fill="#06b6d4" opacity="0.7" />
        {/* Eyes */}
        <circle cx="38" cy="45" r="5" fill="#0ea5e9" opacity="0.8" />
        <circle cx="62" cy="45" r="5" fill="#0ea5e9" opacity="0.8" />
        {/* Mouth */}
        <rect x="35" y="62" width="30" height="3" rx="1.5" fill="#0891b2" opacity="0.7" />
      </svg>

      {/* Neural network nodes - left side */}
      <svg
        className="absolute bottom-16 left-8 w-56 h-56 opacity-60"
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Nodes */}
        <circle cx="30" cy="50" r="8" fill="#3b82f6" opacity="0.7" />
        <circle cx="30" cy="100" r="8" fill="#3b82f6" opacity="0.7" />
        <circle cx="30" cy="150" r="8" fill="#3b82f6" opacity="0.7" />
        
        <circle cx="100" cy="40" r="8" fill="#06b6d4" opacity="0.7" />
        <circle cx="100" cy="100" r="8" fill="#06b6d4" opacity="0.7" />
        <circle cx="100" cy="160" r="8" fill="#06b6d4" opacity="0.7" />
        
        <circle cx="170" cy="75" r="8" fill="#8b5cf6" opacity="0.7" />
        <circle cx="170" cy="125" r="8" fill="#8b5cf6" opacity="0.7" />
        
        {/* Connections */}
        <line x1="38" y1="50" x2="92" y2="40" stroke="#3b82f6" strokeWidth="1.5" opacity="0.4" />
        <line x1="38" y1="50" x2="92" y2="100" stroke="#3b82f6" strokeWidth="1.5" opacity="0.4" />
        <line x1="38" y1="100" x2="92" y2="100" stroke="#3b82f6" strokeWidth="1.5" opacity="0.4" />
        <line x1="38" y1="100" x2="92" y2="160" stroke="#3b82f6" strokeWidth="1.5" opacity="0.4" />
        <line x1="38" y1="150" x2="92" y2="100" stroke="#3b82f6" strokeWidth="1.5" opacity="0.4" />
        <line x1="38" y1="150" x2="92" y2="160" stroke="#3b82f6" strokeWidth="1.5" opacity="0.4" />
        
        <line x1="108" y1="40" x2="162" y2="75" stroke="#06b6d4" strokeWidth="1.5" opacity="0.4" />
        <line x1="108" y1="100" x2="162" y2="75" stroke="#06b6d4" strokeWidth="1.5" opacity="0.4" />
        <line x1="108" y1="100" x2="162" y2="125" stroke="#06b6d4" strokeWidth="1.5" opacity="0.4" />
        <line x1="108" y1="160" x2="162" y2="125" stroke="#06b6d4" strokeWidth="1.5" opacity="0.4" />
      </svg>

      {/* Circuit board pattern - top left */}
      <svg
        className="absolute top-12 left-16 w-40 h-40 opacity-50"
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <line x1="20" y1="20" x2="80" y2="20" stroke="#06b6d4" strokeWidth="2" />
        <line x1="20" y1="50" x2="80" y2="50" stroke="#06b6d4" strokeWidth="2" />
        <line x1="20" y1="80" x2="80" y2="80" stroke="#06b6d4" strokeWidth="2" />
        <line x1="30" y1="10" x2="30" y2="90" stroke="#3b82f6" strokeWidth="2" />
        <line x1="70" y1="10" x2="70" y2="90" stroke="#3b82f6" strokeWidth="2" />
        <circle cx="30" cy="20" r="4" fill="#0ea5e9" />
        <circle cx="70" cy="50" r="4" fill="#0ea5e9" />
        <circle cx="30" cy="80" r="4" fill="#0ea5e9" />
      </svg>

      {/* Binary code pattern */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="binary" x="0" y="0" width="60" height="30" patternUnits="userSpaceOnUse">
            <text x="5" y="15" fontSize="10" fill="#3b82f6" opacity="0.3" fontFamily="monospace">01</text>
            <text x="25" y="15" fontSize="10" fill="#06b6d4" opacity="0.3" fontFamily="monospace">10</text>
            <text x="45" y="15" fontSize="10" fill="#0ea5e9" opacity="0.3" fontFamily="monospace">11</text>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#binary)" />
      </svg>

      {/* Glowing dots */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.6">
          <circle cx="120" cy="60" r="2" fill="#3b82f6" />
          <circle cx="250" cy="90" r="1.5" fill="#06b6d4" />
          <circle cx="380" cy="50" r="1.8" fill="#0ea5e9" />
          <circle cx="520" cy="120" r="1.6" fill="#8b5cf6" />
        </g>
      </svg>
    </div>
  );
};

export default AgentsBackground;

