/**
 * ToolCallsModal Component
 * Displays tool calls made during agent reasoning with input parameters and output results
 */

import React, { useState } from "react";
import { Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { SharedModal } from "./SharedModal";

interface ToolCall {
  toolName: string;
  parameters: Record<string, any>;
  result: any;
  error?: string | null;
}

interface ToolCallsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  toolCalls: ToolCall[];
  agentName?: string;
}

export const ToolCallsModal: React.FC<ToolCallsModalProps> = ({
  open,
  onOpenChange,
  toolCalls,
  agentName,
}) => {
  // Track which tool calls have expanded sections (default: all collapsed)
  const [expandedParams, setExpandedParams] = useState<Set<number>>(new Set());
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set());

  const toggleParams = (idx: number) => {
    setExpandedParams((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const toggleResults = (idx: number) => {
    setExpandedResults((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  return (
    <SharedModal
      open={open}
      onOpenChange={onOpenChange}
      title={`Tools Used${agentName ? ` by ${agentName}` : ""}`}
      size="xl"
    >
      <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
        {toolCalls.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            No tools were used for this reasoning event.
          </div>
        ) : (
          toolCalls.map((toolCall, idx) => (
            <div
              key={idx}
              className="border rounded-lg p-4 space-y-3 bg-card"
            >
              {/* Tool Name Header */}
              <div className="flex items-center gap-2 pb-2 border-b">
                <Wrench className="w-4 h-4 text-brand-orange" />
                <span className="font-semibold text-lg">{toolCall.toolName}</span>
              </div>

              {/* Parameters Section - Collapsible */}
              <div className="space-y-2">
                <button
                  onClick={() => toggleParams(idx)}
                  className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full text-left"
                >
                  {expandedParams.has(idx) ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  Input Parameters
                </button>
                {expandedParams.has(idx) && (
                  <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(toolCall.parameters, null, 2)}
                  </pre>
                )}
              </div>

              {/* Result/Error Section - Collapsible */}
              <div className="space-y-2">
                <button
                  onClick={() => toggleResults(idx)}
                  className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full text-left"
                >
                  {expandedResults.has(idx) ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  {toolCall.error ? "Error" : "Output"}
                </button>
                {expandedResults.has(idx) && (
                  <>
                    {toolCall.error ? (
                      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 p-3 rounded text-sm">
                        {toolCall.error}
                      </div>
                    ) : (
                      <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
                        {typeof toolCall.result === "string"
                          ? toolCall.result
                          : JSON.stringify(toolCall.result, null, 2)}
                      </pre>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </SharedModal>
  );
};

export default ToolCallsModal;

