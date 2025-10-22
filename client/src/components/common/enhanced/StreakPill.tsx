import React from "react";
import { cn } from "@/lib/utils";

interface StreakPillProps { days: number; className?: string; }
export const StreakPill: React.FC<StreakPillProps> = ({ days, className }) => (
  <div className={cn("inline-flex items-center gap-1 rounded-full bg-amber-400/15 text-amber-600 px-2 py-1 text-xs", className)}>
    <span>🔥</span>
    <span>Streak {days}</span>
  </div>
);

