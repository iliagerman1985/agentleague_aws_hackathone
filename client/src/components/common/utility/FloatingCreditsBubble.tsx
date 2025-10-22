import React, { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { BuyCreditsDialog } from "@/components/common/dialogs/BuyCreditsDialog";

// Simple SVG coin stack icon with warm gradient - same as dialog
const CoinStackIcon = ({ className = "" }: { className?: string }) => (
  <svg viewBox="0 0 64 64" className={className} aria-hidden>
    <defs>
      <linearGradient id="coinGradFloat" x1="0" x2="1">
        <stop stopColor="#FDE68A" />
        <stop offset="1" stopColor="#F59E0B" />
      </linearGradient>
    </defs>
    <ellipse cx="32" cy="18" rx="18" ry="8" fill="url(#coinGradFloat)" stroke="#A16207" />
    <ellipse cx="32" cy="28" rx="18" ry="8" fill="url(#coinGradFloat)" stroke="#A16207" />
    <ellipse cx="32" cy="38" rx="18" ry="8" fill="url(#coinGradFloat)" stroke="#A16207" />
  </svg>
);

export const FloatingCreditsBubble: React.FC = () => {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  const balance = user?.coinsBalance ?? 0;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open credits and bundles"
        className="fixed bottom-3 right-2 sm:bottom-6 sm:right-6 z-50 inline-flex items-center gap-2 rounded-full bg-primary text-primary-foreground px-4 py-3 shadow-lg hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 border border-primary/40"
      >
        <CoinStackIcon className="h-4 w-4" />
        <span className="text-sm font-semibold tabular-nums">{balance}</span>
      </button>
      <BuyCreditsDialog open={open} onOpenChange={setOpen} />
    </>
  );
};

export default FloatingCreditsBubble;

