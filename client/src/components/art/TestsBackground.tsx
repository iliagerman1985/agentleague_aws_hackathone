/**
 * Tests-themed background art with test tubes and beakers
 */

import React from "react";
import { cn } from "@/lib/utils";

interface TestsBackgroundProps {
  className?: string;
  opacity?: number;
}

export const TestsBackground: React.FC<TestsBackgroundProps> = ({
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
      {/* Gradient overlays - science lab feel */}
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-200/35 via-transparent to-blue-300/35" />
      <div className="absolute inset-0 bg-gradient-to-tr from-teal-300/25 via-transparent to-cyan-400/25" />

      {/* Large test tube - right side */}
      <svg
        className="absolute top-8 right-12 w-32 h-48 md:w-40 md:h-56 opacity-75"
        viewBox="0 0 100 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Test tube body */}
        <rect x="30" y="20" width="40" height="140" rx="2" fill="#06B6D4" opacity="0.3" stroke="#0891B2" strokeWidth="2" />
        {/* Liquid inside */}
        <rect x="32" y="100" width="36" height="58" fill="#14B8A6" opacity="0.5" />
        {/* Cap/stopper */}
        <rect x="25" y="10" width="50" height="12" rx="2" fill="#0891B2" opacity="0.6" />
        {/* Bubbles */}
        <circle cx="50" cy="130" r="3" fill="#E0F2FE" opacity="0.7" />
        <circle cx="45" cy="145" r="2" fill="#E0F2FE" opacity="0.6" />
        <circle cx="55" cy="140" r="2.5" fill="#E0F2FE" opacity="0.65" />
      </svg>

      {/* Beaker - bottom left */}
      <svg
        className="absolute bottom-12 left-8 w-28 h-36 md:w-36 md:h-44 opacity-70"
        viewBox="0 0 100 140"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Beaker body - trapezoid shape */}
        <path d="M30 10 L70 10 L80 130 L20 130 Z" fill="#0891B2" opacity="0.25" stroke="#06B6D4" strokeWidth="2" />
        {/* Liquid */}
        <path d="M35 80 L65 80 L72 128 L28 128 Z" fill="#14B8A6" opacity="0.45" />
        {/* Measurement lines */}
        <line x1="25" y1="50" x2="35" y2="50" stroke="#0891B2" strokeWidth="1" opacity="0.5" />
        <line x1="25" y1="80" x2="35" y2="80" stroke="#0891B2" strokeWidth="1" opacity="0.5" />
        <line x1="25" y1="110" x2="35" y2="110" stroke="#0891B2" strokeWidth="1" opacity="0.5" />
        {/* Bubbles */}
        <circle cx="50" cy="100" r="2.5" fill="#E0F2FE" opacity="0.7" />
        <circle cx="45" cy="115" r="2" fill="#E0F2FE" opacity="0.6" />
      </svg>

      {/* Flask - center */}
      <svg
        className="absolute top-1/3 left-1/3 w-24 h-32 md:w-28 md:h-36 opacity-65"
        viewBox="0 0 100 140"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Flask neck */}
        <rect x="42" y="10" width="16" height="30" fill="#06B6D4" opacity="0.3" stroke="#0891B2" strokeWidth="1.5" />
        {/* Flask body - triangle */}
        <path d="M42 40 L20 120 L80 120 L58 40 Z" fill="#0891B2" opacity="0.3" stroke="#06B6D4" strokeWidth="2" />
        {/* Liquid */}
        <path d="M35 90 L65 90 L75 118 L25 118 Z" fill="#14B8A6" opacity="0.5" />
        {/* Bubbles */}
        <circle cx="50" cy="100" r="2" fill="#E0F2FE" opacity="0.7" />
      </svg>

      {/* Small test tube - bottom right */}
      <svg
        className="absolute bottom-20 right-1/4 w-16 h-24 opacity-60"
        viewBox="0 0 60 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="20" y="15" width="20" height="90" rx="1" fill="#06B6D4" opacity="0.3" stroke="#0891B2" strokeWidth="1.5" />
        <rect x="22" y="70" width="16" height="33" fill="#14B8A6" opacity="0.5" />
        <rect x="17" y="8" width="26" height="8" rx="1" fill="#0891B2" opacity="0.5" />
      </svg>

      {/* Checkmark icons scattered */}
      <svg className="absolute top-20 left-20 w-12 h-12 opacity-50" viewBox="0 0 24 24" fill="none" stroke="#14B8A6" strokeWidth="2">
        <path d="M20 6L9 17l-5-5" />
      </svg>

      <svg className="absolute bottom-1/3 right-1/3 w-10 h-10 opacity-45" viewBox="0 0 24 24" fill="none" stroke="#06B6D4" strokeWidth="2">
        <path d="M20 6L9 17l-5-5" />
      </svg>

      {/* Molecule/atom pattern */}
      <svg
        className="absolute top-1/2 right-1/4 w-20 h-20 opacity-40"
        viewBox="0 0 100 100"
        fill="none"
        stroke="#0891B2"
        strokeWidth="1.5"
      >
        <circle cx="50" cy="50" r="6" fill="#06B6D4" opacity="0.6" />
        <circle cx="30" cy="30" r="4" fill="#14B8A6" opacity="0.5" />
        <circle cx="70" cy="30" r="4" fill="#14B8A6" opacity="0.5" />
        <circle cx="70" cy="70" r="4" fill="#14B8A6" opacity="0.5" />
        <line x1="50" y1="50" x2="30" y2="30" />
        <line x1="50" y1="50" x2="70" y2="30" />
        <line x1="50" y1="50" x2="70" y2="70" />
      </svg>
    </div>
  );
};

export default TestsBackground;

