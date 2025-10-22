import React from "react";
import { cn } from "@/lib/utils";

interface ShineBorderCardProps {
  children: React.ReactNode;
  className?: string;
}

// Simple shine border effect using gradients (Magic UI style)
export const ShineBorderCard: React.FC<ShineBorderCardProps> = ({ children, className }) => {
  return (
    <div className={cn("relative rounded-xl border border-border/60 shadow-sm", className)}>
      <div className="rounded-xl bg-card p-4">
        {children}
      </div>
    </div>
  );
};

