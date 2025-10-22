import React from "react";
import { cn } from "@/lib/utils";

interface XPProgressProps { value: number; className?: string; }
export const XPProgress: React.FC<XPProgressProps> = ({ value, className }) => (
  <div className={cn("h-2 w-full rounded bg-muted overflow-hidden", className)}>
    <div style={{ width: `${Math.min(100, Math.max(0, value))}%` }} className="h-2 rounded bg-primary" />
  </div>
);

