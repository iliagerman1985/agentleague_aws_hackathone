import React from "react";
import { cn } from "@/lib/utils";

interface BrandSparklesProps {
  children?: React.ReactNode;
  className?: string;
}

// Lightweight sparkles accent wrapper (use sparingly)
export const BrandSparkles: React.FC<BrandSparklesProps> = ({ children, className }) => {
  return (
    <div className={cn("relative", className)}>
      <div className="relative">{children}</div>
    </div>
  );
};

