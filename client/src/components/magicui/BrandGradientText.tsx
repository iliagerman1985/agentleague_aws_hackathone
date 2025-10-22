import React from "react";
import { cn } from "@/lib/utils";

interface BrandGradientTextProps {
  children: React.ReactNode;
  className?: string;
}

export const BrandGradientText: React.FC<BrandGradientTextProps> = ({ children, className }) => {
  return (
    <span
      className={cn(
        "text-foreground",
        className
      )}
    >
      {children}
    </span>
  );
};

