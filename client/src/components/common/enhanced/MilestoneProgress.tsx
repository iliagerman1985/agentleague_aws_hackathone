import React from "react";
import { cn } from "@/lib/utils";

interface Milestone { label: string; value: number; }
export const MilestoneProgress: React.FC<{ value: number; milestones?: Milestone[]; className?: string }>
= ({ value, milestones = [{ label: "Bronze", value: 25 }, { label: "Silver", value: 50 }, { label: "Gold", value: 75 }], className }) => {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("space-y-2", className)}>
      <div className="h-2 w-full rounded bg-muted relative overflow-hidden">
        <div className="h-2 bg-primary rounded" style={{ width: `${clamped}%` }} />
        {milestones.map((m) => (
          <div key={m.label} className="absolute top-0 -translate-x-1/2" style={{ left: `${m.value}%` }}>
            <div className="h-2 w-[2px] bg-border" />
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        {milestones.map((m) => (
          <span key={m.label} style={{ transform: `translateX(calc(${m.value}% - 50%))` }}>{m.label}</span>
        ))}
      </div>
    </div>
  );
};

