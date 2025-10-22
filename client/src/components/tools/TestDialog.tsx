import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TestOutputPanel } from "./TestOutputPanel";
import { FlaskConical, Play } from "lucide-react";
import { GameStatePreview } from "@/components/games/GameStatePreview";
import { GameEnvironment } from "@/types/game";

interface TestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRun: (eventJson: string) => Promise<void>;
  initialEventJson?: string;
  detachable?: boolean;
  // streaming state (controlled by parent)
  running?: boolean;
  logs?: string[];
  status?: "idle" | "running" | "passed" | "failed";
  // When a test fails, allow user to auto-send the output to chat for fixing
  onAttemptFix?: (outputText: string) => void;
  // Environment for showing state preview
  environment?: GameEnvironment;
}

export const TestDialog: React.FC<TestDialogProps> = ({
  open,
  onOpenChange,
  onRun,
  initialEventJson = '',
  running = false,
  logs = [],
  status = "idle",
  onAttemptFix,
  environment,
}) => {
  const [eventJson, setEventJson] = useState(initialEventJson);
  const [hasEdited, setHasEdited] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isScrolledUp, setIsScrolledUp] = useState(false);
  const scrollCheckTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Update eventJson when initialEventJson changes (e.g., when JSON is generated)
  useEffect(() => {
    if (initialEventJson) {
      setEventJson(initialEventJson);
      setHasEdited(false); // Reset edited flag when new JSON is loaded
    }
  }, [initialEventJson]);

  // Track user scroll position
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !open) return;

    const handleScroll = () => {
      // Clear any pending timeout
      if (scrollCheckTimeoutRef.current) {
        clearTimeout(scrollCheckTimeoutRef.current);
      }

      // Debounce the scroll check to avoid interfering with smooth scrolls
      scrollCheckTimeoutRef.current = setTimeout(() => {
        if (!container) return;
        const { scrollTop, scrollHeight, clientHeight } = container;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

        // Consider "at bottom" if within 150px
        const isAtBottom = distanceFromBottom <= 150;
        setIsScrolledUp(!isAtBottom);
      }, 200);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      container.removeEventListener('scroll', handleScroll);
      if (scrollCheckTimeoutRef.current) {
        clearTimeout(scrollCheckTimeoutRef.current);
      }
    };
  }, [open]);

  // Auto-scroll to bottom when dialog opens or when test output updates (only if not scrolled up)
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!open || !container || isScrolledUp) return;

    // Use requestAnimationFrame to wait for DOM updates, then scroll
    const rafId = requestAnimationFrame(() => {
      if (container && !isScrolledUp) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        });
      }
    });

    return () => cancelAnimationFrame(rafId);
  }, [open, logs, status, isScrolledUp]);

  // Reset scroll state when dialog opens
  useEffect(() => {
    if (open) {
      setIsScrolledUp(false);
    }
  }, [open]);

  const handleRun = () => {
    // Keep dialog open; parent controls streaming state
    setHasEdited(false); // Reset edited flag when running test
    onRun(eventJson);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-5xl max-h-[90vh] p-0 flex flex-col">
        <DialogHeader className="px-6 pt-6 pb-4 flex-none">
          <DialogTitle className="text-xl font-semibold flex items-center gap-2">
            <FlaskConical className="h-5 w-5" />
            Test Tool
          </DialogTitle>
          <DialogDescription className="text-base">
            Provide input data to test your tool function. The data will be passed as the event parameter.
          </DialogDescription>
        </DialogHeader>

        {/* Scrollable content area */}
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto scrollbar-visible min-h-0">
          <div className="px-6 pb-4">
          <label className="block text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            Event JSON (Tool Input)
          </label>
          <Textarea
            value={eventJson}
            onChange={(e) => {
              setEventJson(e.target.value);
              setHasEdited(true); // Mark as edited when user changes the JSON
            }}
            className="h-40 font-mono resize-none overflow-y-scroll scrollbar-visible"
            placeholder='{\n  "name": "example",\n  "value": 42,\n  "enabled": true\n}'
          />
          </div>

          {/* State Preview - Show visual representation for game environments */}
          {environment && eventJson.trim() && (
            <div className="px-6 pb-4">
              <label className="block text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
                State Preview
              </label>
              <div className="border rounded-lg bg-card p-4">
                <GameStatePreview
                  environment={environment}
                  jsonText={eventJson}
                  hideCapturedPieces={true}
                  size="small"
                />
              </div>
            </div>
          )}

          {/* Live Output - Fixed height container with proper scroll */}
          <div className="px-6 pb-4">
            <TestOutputPanel logs={logs ?? []} status={status} className="w-full" heightClass="h-80" collapsible={false} />
          </div>

          {/* Failure hint */}
          {status === "failed" && (
            <div className="px-6 pb-4 text-sm text-amber-700 dark:text-amber-300">
              Test failed. Click “Attempt to fix” to send the full error to the AI and request an automatic fix.
            </div>
          )}
        </div>

        <DialogFooter className="px-6 sm:py-4 py-5 flex-none border-t bg-background gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="text-base"
            disabled={running}
          >
            Close
          </Button>
          <Button
            variant="outline"
            onClick={() => { try { navigator.clipboard.writeText((logs || []).join("\n")); } catch {} }}
            className="text-base"
            disabled={running || !(logs && logs.length)}
            title="Copy the output to clipboard"
            data-testid="copy-test-output"
          >
            Copy Output
          </Button>
          {status === "failed" && (
            <Button
              onClick={() => onAttemptFix?.((logs || []).join("\n"))}
              className="text-base"
              disabled={running || !(logs && logs.length)}
              title="Send the error output to chat and ask the AI to fix the tool"
              data-testid="attempt-fix"
            >
              Attempt to fix
            </Button>
          )}
          <Button
            onClick={status === "passed" && !hasEdited ? () => onOpenChange(false) : handleRun}
            data-testid="run-tool"
            className="button-primary text-base flex items-center gap-2"
            disabled={running}
          >
            {running ? "Running…" : (status === "passed" && !hasEdited) ? "OK" : (
              <>
                <Play className="h-4 w-4" />
                Run Tool
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TestDialog;
