import React from 'react';
import type { ChessStateView } from '@/types/chess';
import type { PlayerId } from '@/types/ids';

interface ChessClocksProps {
  state: ChessStateView;
  // Order is [whitePlayerId, blackPlayerId]
  players: [PlayerId, PlayerId];
  // Who is the current player id from the server perspective
  currentPlayerId: PlayerId;
  className?: string;
  // Which clocks to render: both (default), white, or black. Useful for side placement.
  render?: "both" | "white" | "black";
}

function formatMs(ms: number): string {
  const clamped = Math.max(0, Math.floor(ms));
  const totalSec = Math.floor(clamped / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  const mm = m.toString();
  const ss = s < 10 ? `0${s}` : `${s}`;
  return `${mm}:${ss}`;
}

export const ChessClocks: React.FC<ChessClocksProps> = ({ state, players, currentPlayerId, className, render = "both" }) => {
  const [whiteId, blackId] = players;

  const [nowMs, setNowMs] = React.useState<number>(() => Date.now());

  React.useEffect(() => {
    // Stop countdown if game is finished
    if (state.isFinished) return;

    // Smooth countdown only for the active side
    const id = window.setInterval(() => setNowMs(Date.now()), 200);
    return () => window.clearInterval(id);
  }, [state.isFinished]);

  const displayMs = React.useMemo(() => {
    const remaining = state.remainingTimeMs;
    const lastTs = state.lastTimestampMs ?? null;
    const isActive = (pid: PlayerId) => pid === currentPlayerId;

    const calc = (pid: PlayerId) => {
      const base = remaining[pid] ?? 0;
      if (lastTs == null || !isActive(pid)) return base;
      // Active player's local countdown for UX (server is source of truth)
      const elapsed = Math.max(0, nowMs - lastTs);
      return base - elapsed;
    };

    return {
      white: calc(whiteId),
      black: calc(blackId),
    };
  }, [state.remainingTimeMs, state.lastTimestampMs, currentPlayerId, nowMs, whiteId, blackId]);

  const isWhiteActive = currentPlayerId === whiteId;
  const isBlackActive = currentPlayerId === blackId;

  if (render === 'white') {
    return (
      <div className={className ?? ''}>
        <div className={`rounded-lg px-3 py-2 border transition-colors ${isWhiteActive ? 'border-brand-teal bg-white/70 dark:bg-white/10' : 'border-border/50 bg-white/40 dark:bg-white/5'}`}>
          <div className="text-[11px] opacity-70 mb-0.5">White</div>
          <div className="text-xl font-semibold tabular-nums">{formatMs(displayMs.white)}</div>
        </div>
      </div>
    );
  }

  if (render === 'black') {
    return (
      <div className={className ?? ''}>
        <div className={`rounded-lg px-3 py-2 border text-right transition-colors ${isBlackActive ? 'border-brand-teal bg-white/70 dark:bg-white/10' : 'border-border/50 bg-white/40 dark:bg-white/5'}`}>
          <div className="text-[11px] opacity-70 mb-0.5">Black</div>
          <div className="text-xl font-semibold tabular-nums">{formatMs(displayMs.black)}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={className ?? ''}>
      <div className="grid grid-cols-2 gap-2">
        <div className={`rounded-lg px-3 py-2 border transition-colors ${isWhiteActive ? 'border-brand-teal bg-white/70 dark:bg-white/10' : 'border-border/50 bg-white/40 dark:bg-white/5'}`}>
          <div className="text-[11px] opacity-70 mb-0.5">White</div>
          <div className="text-xl font-semibold tabular-nums">{formatMs(displayMs.white)}</div>
        </div>
        <div className={`rounded-lg px-3 py-2 border text-right transition-colors ${isBlackActive ? 'border-brand-teal bg-white/70 dark:bg-white/10' : 'border-border/50 bg-white/40 dark:bg-white/5'}`}>
          <div className="text-[11px] opacity-70 mb-0.5">Black</div>
          <div className="text-xl font-semibold tabular-nums">{formatMs(displayMs.black)}</div>
        </div>
      </div>
    </div>
  );
};

export default ChessClocks;

