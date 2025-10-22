import React, { useState } from "react";

interface TestOutputPanelProps {
  logs: string[];
  status?: "idle" | "running" | "passed" | "failed";
  className?: string;
  onClear?: () => void;
  // Optional collapse controls (shown by default)
  collapsible?: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
  // Default collapsed state when using internal state
  defaultCollapsed?: boolean;
  // Height utility class for the scrollable output area
  heightClass?: string; // e.g. "h-64", "h-[35vh]", "h-full", "flex-1 min-h-0"
}

const statusColors: Record<NonNullable<TestOutputPanelProps["status"]>, string> = {
  idle: "bg-secondary/50 text-muted-foreground",
  running: "bg-amber-500/30 text-amber-800 dark:text-amber-200",
  passed: "bg-emerald-500/30 text-emerald-800 dark:text-emerald-200",
  failed: "bg-red-500/40 text-red-900 dark:text-red-100 font-semibold border border-red-500/50",
};

export const TestOutputPanel: React.FC<TestOutputPanelProps> = ({
  logs,
  status = "idle",
  className,
  onClear,
  collapsible = true,
  collapsed,
  onToggle,
  defaultCollapsed = false,
  heightClass = "h-80"
}) => {
  const [internalCollapsed, setInternalCollapsed] = useState(defaultCollapsed);
  const effectiveCollapsed = collapsed ?? internalCollapsed;
  const handleToggle = () => {
    if (onToggle) onToggle();
    else setInternalCollapsed((c) => !c);
  };

  return (
    <div className={"rounded-lg border border-border bg-card " + (className ?? "")}>
      <div className={`flex items-center justify-between px-4 py-3 border-b border-border text-base`}>
        <div className="flex items-center gap-2">
          {collapsible && (
            <button
              onClick={handleToggle}
              className="text-sm px-3 py-1 rounded-md bg-slate-200 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition-colors"
              aria-label={effectiveCollapsed ? "Expand output" : "Collapse output"}
            >
              {effectiveCollapsed ? "Expand" : "Collapse"}
            </button>
          )}
          <span className="font-medium text-foreground">Test Output</span>
        </div>
        <div className="flex items-center gap-2">
          {onClear && logs.length > 0 && (
            <button
              onClick={onClear}
              className="text-sm px-3 py-1 rounded-md bg-slate-200 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition-colors"
            >
              Clear
            </button>
          )}
          <span data-testid="test-result-status" data-status={status} className={`rounded-md px-3 py-1 text-base font-semibold ${statusColors[status]}`}>{status.toUpperCase()}</span>
        </div>
      </div>
      <div
        data-testid="test-output"
        className={`${effectiveCollapsed ? "hidden" : heightClass + " overflow-y-scroll scrollbar-visible overscroll-contain touch-pan-y"} p-4 pr-3 font-mono text-base text-foreground bg-background/60`}
      >
        {logs.length === 0 ? (
          <div className="text-muted-foreground text-base text-center py-8">No output yet. Run your code to see results here.</div>
        ) : (
          logs.map((l, idx) => (
            <div key={idx} className="whitespace-pre-wrap leading-relaxed">{l}</div>
          ))
        )}
      </div>
    </div>
  );
};

export default TestOutputPanel;
