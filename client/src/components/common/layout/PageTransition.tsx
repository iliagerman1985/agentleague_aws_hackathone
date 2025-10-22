import React from "react";
import { useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

interface PageTransitionProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Simple CSS-only page enter animation keyed by pathname.
 * This avoids extra dependencies and still gives a dramatic entrance.
 */
export const PageTransition: React.FC<PageTransitionProps> = ({ children, className }) => {
  const location = useLocation();

  return (
    <div key={location.pathname} className={cn("animate-dramaticIn", "h-full", className)}>
      {children}
    </div>
  );
};

export default PageTransition;

