/**
 * Page background wrapper with themed decorations
 * Provides consistent background styling across pages
 */

import React from "react";
import { cn } from "@/lib/utils";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";

interface PageBackgroundProps {
  children: React.ReactNode;
  environment?: string;
  variant?: "geometric" | "dots" | "waves" | "grid";
  className?: string;
}

export const PageBackground: React.FC<PageBackgroundProps> = ({
  children,
  environment,
  variant = "geometric",
  className
}) => {
  return (
    <div className={cn("relative", className || "min-h-full")}>
      <EnvironmentBackground
        environment={environment}
        variant={variant}
        opacity={0.04}
      />
      <div className="relative z-10 h-full">
        {children}
      </div>
    </div>
  );
};

