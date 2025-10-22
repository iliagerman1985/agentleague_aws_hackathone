import { useCallback, useMemo, useRef, useState } from "react";

/**
 * Generic client-side history manager for undo/redo over immutable snapshots.
 * - reset(initial): set timeline to [initial]
 * - push(next): append next; if not at latest, truncate future first
 * - undo/redo: move the current index
 */
export function useStateHistory<T>() {
  const [history, setHistory] = useState<T[]>([]);
  const [index, setIndex] = useState<number>(-1);
  const lastPushedRef = useRef<T | null>(null);

  const current = useMemo(() => (index >= 0 ? history[index] : null), [history, index]);
  const canUndo = index > 0;
  const canRedo = index >= 0 && index < history.length - 1;

  const reset = useCallback((initial: T) => {
    setHistory([initial]);
    setIndex(0);
    lastPushedRef.current = initial;
  }, []);

  const push = useCallback(
    (next: T) => {
      // Avoid pushing identical reference twice in a row (cheap guard)
      if (lastPushedRef.current === next) return;
      setHistory((h) => (index < h.length - 1 ? [...h.slice(0, index + 1), next] : [...h, next]));
      setIndex((i) => i + 1);
      lastPushedRef.current = next;
    },
    [index]
  );

  const undo = useCallback(() => {
    if (canUndo) setIndex((i) => i - 1);
  }, [canUndo]);

  const redo = useCallback(() => {
    if (canRedo) setIndex((i) => i + 1);
  }, [canRedo]);

  return { history, index, current, canUndo, canRedo, reset, push, undo, redo };
}

