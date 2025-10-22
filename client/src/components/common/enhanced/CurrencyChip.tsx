import React from "react";
import { cn } from "@/lib/utils";

interface CurrencyChipProps { amount: number; className?: string; }
export const CurrencyChip: React.FC<CurrencyChipProps> = ({ amount, className }) => (
  <div className={cn("inline-flex items-center gap-1 rounded-full bg-brand-lime/15 text-brand-lime px-2 py-1 text-xs", className)}>
    <span>🪙</span>
    <span className="font-medium">{amount.toLocaleString()}</span>
  </div>
);

