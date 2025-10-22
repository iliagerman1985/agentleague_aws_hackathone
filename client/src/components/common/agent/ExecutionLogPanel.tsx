import React from "react";
import { Card } from "@/components/ui/card";
import { LoadingDots } from "@/components/magicui/LoadingDots";
import { Terminal, Wrench, AlertTriangle, ChevronRight } from "lucide-react";

export interface ExecutionLogPanelProps {
  steps: Array<
    | { type: "system"; text: string }
    | { type: "assistant"; text?: string; model?: string; reasoning?: string }
    | { type: "tool"; toolName: string; parameters: Record<string, any>; output?: any }
    | { type: "validation"; errors: string[] }
    | { type: "final"; action: any; reasoning: string }
  >;
  running?: boolean;
  title?: string;
  className?: string;
  executionLogRef?: React.RefObject<HTMLDivElement>;
  renderToolOutput?: (output: any) => JSX.Element;
  renderFinalAction?: (action: any) => JSX.Element;
}

export const ExecutionLogPanel: React.FC<ExecutionLogPanelProps> = ({
  steps,
  running = false,
  title = "Execution Log",
  className,
  executionLogRef,
  renderToolOutput = (o) => <pre className="whitespace-pre-wrap text-sm break-words bg-muted p-2 rounded">{JSON.stringify(o, null, 2)}</pre>,
  renderFinalAction = (a) => <pre className="whitespace-pre-wrap text-sm break-words bg-muted p-2 rounded">{JSON.stringify(a, null, 2)}</pre>,
}) => {
  return (
    <Card className={"p-4 lg:p-6 flex flex-col h-[70svh] md:h-[74vh] min-h-0 overflow-hidden " + (className ?? "")}>
      <div className="flex items-center justify-between mb-3 lg:mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">{title}</h3>
        </div>
      </div>
      <div ref={executionLogRef} className="flex-1 space-y-3 overflow-y-auto pr-2 min-h-0 max-h-[60vh]">
        {steps.length === 0 && !running && (
          <div className="text-muted-foreground text-sm">No output yet. Start a run to see progress.</div>
        )}
        {steps.length === 0 && running && (
          <div className="flex items-center justify-center py-8">
            <LoadingDots />
          </div>
        )}
        {steps.map((s, i) => (
          <div key={i} className="flex items-start gap-2">
            {s.type === "assistant" && (
              <>
                <Terminal className="h-4 w-4 mt-1 text-brand-teal flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-muted-foreground">Assistant {"model" in s && s.model ? `(${s.model})` : ""}</div>
                  {"reasoning" in s && s.reasoning && (
                    <div className="mt-1">
                      <div className="text-xs font-semibold">Reasoning:</div>
                      <pre className="whitespace-pre-wrap text-sm break-words">{s.reasoning}</pre>
                    </div>
                  )}
                </div>
              </>
            )}
            {s.type === "tool" && (
              <>
                <Wrench className="h-4 w-4 mt-1 text-brand-orange flex-shrink-0" />
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="text-xs text-muted-foreground">Tool {s.toolName}</div>
                  <div className="text-xs">
                    <span className="font-medium">Parameters:</span>
                    <pre className="whitespace-pre-wrap text-sm break-words bg-muted p-2 rounded mt-1">{JSON.stringify(s.parameters, null, 2)}</pre>
                  </div>
                  <div className="text-xs">
                    <span className="font-medium">Output:</span>
                    <div className="mt-1">{renderToolOutput(s.output)}</div>
                  </div>
                </div>
              </>
            )}
            {s.type === "validation" && (
              <>
                <AlertTriangle className="h-4 w-4 mt-1 text-yellow-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-muted-foreground">Validation errors</div>
                  <ul className="list-disc ml-5 text-sm">
                    {s.errors.map((e, j) => (
                      <li key={j} className="break-words">
                        {e}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
            {s.type === "system" && (
              <>
                <ChevronRight className="h-4 w-4 mt-1 text-muted-foreground flex-shrink-0" />
                <div className="text-sm text-muted-foreground break-words flex-1 min-w-0">{s.text}</div>
              </>
            )}
            {s.type === "final" && (
              <>
                <div className="flex-1 min-w-0">
                  <div className="inline-block px-2 py-1 rounded-md border border-border bg-muted/40 text-foreground text-base lg:text-lg font-semibold">Final Decision</div>
                  <div className="mt-2">
                    <div className="text-xs font-semibold">Reasoning:</div>
                    <pre className="whitespace-pre-wrap text-sm break-words">{s.reasoning}</pre>
                  </div>
                  <div className="mt-2">
                    <div className="text-xs font-semibold">Action:</div>
                    <div className="mt-1">{renderFinalAction(s.action)}</div>
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
};

export default ExecutionLogPanel;

