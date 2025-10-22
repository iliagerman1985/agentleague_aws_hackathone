import React from "react";
import { cn } from "@/lib/utils";

interface LevelBadgeProps { level?: number; label?: string; className?: string; }
export const LevelBadge: React.FC<LevelBadgeProps> = ({ level = 1, label = "Novice", className }) => (
  <div className={cn("inline-flex items-center gap-1 rounded-full bg-brand-blue/10 text-brand-blue px-2 py-1 text-xs", className)}>
    <span className="font-bold">LVL {level}</span>
    <span className="opacity-70">{label}</span>
  </div>
);

