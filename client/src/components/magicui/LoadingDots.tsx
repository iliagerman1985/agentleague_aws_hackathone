import React from "react";
import { cn } from "@/lib/utils";

interface LoadingDotsProps { className?: string; }

export const LoadingDots: React.FC<LoadingDotsProps> = ({ className }) => {
  return (
    <div className={cn("flex items-center gap-1", className)} aria-label="loading">
      <span className="size-1.5 rounded-full bg-brand-orange animate-pulse" />
      <span className="size-1.5 rounded-full bg-brand-orange animate-pulse [animation-delay:120ms]" />
      <span className="size-1.5 rounded-full bg-brand-orange animate-pulse [animation-delay:240ms]" />
    </div>
  );
};

