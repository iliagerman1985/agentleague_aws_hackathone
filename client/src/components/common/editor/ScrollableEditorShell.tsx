import React from "react";
import { cn } from "@/lib/utils";

interface ScrollableEditorShellProps {
  children: React.ReactNode;
  className?: string;
  maxHeight?: string; // e.g., "65vh"
  borderClassName?: string;
  backgroundClassName?: string;
}

/**
 * A reusable scrollable editor container that matches the Tool CodeEditor chrome.
 * - Provides rounded border, background, and a scrollable region with a configurable max height
 * - Ensures min-h-0 so it works inside flex layouts
 */
export const ScrollableEditorShell: React.FC<ScrollableEditorShellProps> = ({
  children,
  className,
  maxHeight = "65vh",
  borderClassName = "border-border",
  backgroundClassName = "bg-card",
}) => {
  const disableMax = maxHeight === "none";
  const fullHeight = maxHeight === "100%";
  
  return (
    <div
      className={cn(
        "relative w-full min-h-0 rounded-xl border scrollbar-stable",
        disableMax ? "overflow-visible h-auto" : "overflow-y-auto",
        fullHeight ? "h-full" : "",
        borderClassName,
        backgroundClassName,
        className
      )}
      style={disableMax || fullHeight ? undefined : { maxHeight }}
      data-testid="scrollable-editor-shell"
    >
      {children}
    </div>
  );
};

export default ScrollableEditorShell;

