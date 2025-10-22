import React from "react";
import { cn } from "@/lib/utils";

export type SpinnerSize = "sm" | "md" | "lg";
export type SpinnerVariant = "brand" | "neutral";

interface SpinnerProps {
  size?: SpinnerSize;
  variant?: SpinnerVariant;
  className?: string;
  label?: string;
}

const sizeMap: Record<SpinnerSize, string> = {
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-[3px]",
  lg: "h-10 w-10 border-4",
};

export const Spinner: React.FC<SpinnerProps> = ({ size = "md", variant = "brand", className, label }) => {
  const base = cn(
    "inline-block animate-spin rounded-full",
    sizeMap[size],
    variant === "brand"
      ? "border-muted-foreground/30 border-t-brand-orange"
      : "border-muted-foreground/30 border-t-muted-foreground",
    className
  );

  return (
    <div className="inline-flex items-center gap-2" role="status" aria-live="polite">
      <div className={base} />
      {label ? <span className="text-sm text-muted-foreground">{label}</span> : null}
    </div>
  );
};

