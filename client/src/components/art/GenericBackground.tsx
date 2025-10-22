/**
 * Generic background art component
 * Displays abstract geometric patterns for non-game pages
 */

import React from "react";
import { cn } from "@/lib/utils";

interface GenericBackgroundProps {
  className?: string;
  opacity?: number;
  variant?: "geometric" | "dots" | "waves" | "grid";
}

export const GenericBackground: React.FC<GenericBackgroundProps> = ({ 
  className,
  opacity = 0.03,
  variant = "geometric"
}) => {
  if (variant === "dots") {
    return (
      <div
        className={cn("absolute inset-0 overflow-hidden pointer-events-none min-h-full", className)}
        style={{ opacity }}
      >
        <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
          <defs>
            <pattern id="dots" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="20" cy="20" r="2" fill="#0891B2" opacity="0.4" />
              <circle cx="10" cy="30" r="1.5" fill="#06B6D4" opacity="0.3" />
              <circle cx="30" cy="10" r="1.5" fill="#14B8A6" opacity="0.3" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#dots)" />
        </svg>
      </div>
    );
  }

  if (variant === "waves") {
    return (
      <div
        className={cn("absolute inset-0 overflow-hidden pointer-events-none min-h-full", className)}
        style={{ opacity }}
      >
        <svg className="absolute bottom-0 left-0 w-full h-1/2" viewBox="0 0 1200 400" preserveAspectRatio="xMidYMid slice">
          <path d="M0,100 C300,200 600,0 900,100 C1050,150 1200,50 1200,50 L1200,400 L0,400 Z" fill="#06B6D4" opacity="0.25" />
          <path d="M0,200 C300,100 600,300 900,200 C1050,150 1200,250 1200,250 L1200,400 L0,400 Z" fill="#0891B2" opacity="0.2" />
          <path d="M0,250 C300,300 600,200 900,250 C1050,275 1200,225 1200,225 L1200,400 L0,400 Z" fill="#14B8A6" opacity="0.15" />
        </svg>
      </div>
    );
  }

  if (variant === "grid") {
    return (
      <div
        className={cn("absolute inset-0 overflow-hidden pointer-events-none min-h-full", className)}
        style={{ opacity }}
      >
        <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
          <defs>
            <pattern id="grid" x="0" y="0" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#0891B2" strokeWidth="1" opacity="0.3" />
              <circle cx="0" cy="0" r="2" fill="#06B6D4" opacity="0.4" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>
    );
  }

  // Default: geometric
  return (
    <div
      className={cn("absolute inset-0 overflow-hidden pointer-events-none min-h-full", className)}
      style={{ opacity }}
    >
      {/* Large circle - cyan */}
      <svg
        className="absolute -top-20 -right-20 w-96 h-96 opacity-20"
        viewBox="0 0 200 200"
        fill="none"
        stroke="#06B6D4"
        strokeWidth="1"
      >
        <circle cx="100" cy="100" r="80" />
        <circle cx="100" cy="100" r="60" />
        <circle cx="100" cy="100" r="40" />
      </svg>

      {/* Triangle pattern - teal */}
      <svg
        className="absolute bottom-20 left-10 w-64 h-64 opacity-15"
        viewBox="0 0 200 200"
        fill="#0891B2"
      >
        <polygon points="100,20 180,180 20,180" opacity="0.3" />
        <polygon points="100,60 150,150 50,150" opacity="0.2" />
      </svg>

      {/* Hexagon - mint/teal */}
      <svg
        className="absolute top-1/3 left-1/3 w-48 h-48 opacity-25"
        viewBox="0 0 100 100"
        fill="none"
        stroke="#14B8A6"
        strokeWidth="1.5"
      >
        <polygon points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5" />
        <polygon points="50,15 80,32.5 80,67.5 50,85 20,67.5 20,32.5" />
      </svg>

      {/* Small squares - cyan/teal mix */}
      <svg
        className="absolute bottom-1/4 right-1/4 w-32 h-32 opacity-20"
        viewBox="0 0 100 100"
        fill="#0891B2"
      >
        <rect x="10" y="10" width="30" height="30" opacity="0.3" />
        <rect x="60" y="10" width="30" height="30" opacity="0.2" fill="#06B6D4" />
        <rect x="10" y="60" width="30" height="30" opacity="0.25" fill="#14B8A6" />
        <rect x="60" y="60" width="30" height="30" opacity="0.15" />
      </svg>
    </div>
  );
};

