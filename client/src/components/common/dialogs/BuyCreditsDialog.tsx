import React, { useEffect, useMemo, useState } from "react";
import { SharedModal } from "@/components/common/SharedModal";
import { DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

interface BuyCreditsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface Bundle {
  id: string;
  name: string;
  coins: number;
  currency: string;
  amount_cents: number;
  price_id?: string;
}

// Simple SVG coin stack icon with warm gradient
const CoinStackIcon = ({ className = "" }: { className?: string }) => (
  <svg viewBox="0 0 64 64" className={className} aria-hidden>
    <defs>
      <linearGradient id="coinGrad" x1="0" x2="1">
        <stop stopColor="#FDE68A" />
        <stop offset="1" stopColor="#F59E0B" />
      </linearGradient>
    </defs>
    <ellipse cx="32" cy="18" rx="18" ry="8" fill="url(#coinGrad)" stroke="#A16207" />
    <ellipse cx="32" cy="28" rx="18" ry="8" fill="url(#coinGrad)" stroke="#A16207" />
    <ellipse cx="32" cy="38" rx="18" ry="8" fill="url(#coinGrad)" stroke="#A16207" />
  </svg>
);

const Ribbon = ({ text }: { text: string }) => (
  <span className="absolute top-2 left-2 z-10 pointer-events-none rounded-md bg-gradient-to-r from-brand-teal to-emerald-600 px-2 py-0.5 text-xs font-semibold text-white shadow">
    {text}
  </span>
);

export const BuyCreditsDialog: React.FC<BuyCreditsDialogProps> = ({ open, onOpenChange }) => {
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { refreshUser, user } = useAuth();
  const basePricePerCoin = useMemo(() => {
    if (!bundles.length) return undefined as number | undefined;
    return Math.min(...bundles.map(b => (b.amount_cents / 100) / b.coins));
  }, [bundles]);

  const selectedBundle = useMemo(() => {
    return bundles.find(b => b.id === selected) || null;
  }, [bundles, selected]);

  const maxSavings = useMemo(() => {
    if (!basePricePerCoin) return 0;
    return Math.max(
      0,
      ...bundles.map(b => {
        const price = b.amount_cents / 100;
        const ppc = price / b.coins;
        return Math.max(0, Math.round((1 - ppc / basePricePerCoin) * 100));
      })
    );
  }, [bundles, basePricePerCoin]);


  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const resp = await api.billing.listBundles();
        setBundles(resp.bundles || []);
        if ((resp.bundles || []).length > 0) setSelected(resp.bundles[0].id);
      } catch (e) {
        console.error("Failed to load bundles", e);
      }
    })();
  }, [open]);

  const handleBuy = async () => {
    if (!selected) return;
    setLoading(true);
    try {
      const resp = await api.billing.createCheckoutSession(selected);
      try {
        sessionStorage.setItem("preCheckoutPath", window.location.pathname + window.location.search);
      } catch {}
      window.location.href = resp.checkout_url;
    } catch (e) {
      console.error("Failed to start checkout", e);
    } finally {
      setLoading(false);
      setTimeout(() => refreshUser(), 2000);
    }
  };

  return (
    <SharedModal open={open} onOpenChange={onOpenChange} title="Buy Game Coins" size="lg" className="max-w-2xl rounded-xl border bg-card text-foreground border-border backdrop-blur">
        {maxSavings > 0 && (
          <p className="text-sm text-muted-foreground">Get more for less — save up to {maxSavings}%</p>
        )}
        {/* Local animation keyframes for shimmer */}
        <style>{`@keyframes bundleShimmer { 0% { transform: translateX(-150%); } 100% { transform: translateX(150%); } }`}</style>

        <div className="grid gap-4 sm:grid-cols-2">
          {bundles.map((b) => {
            const price = b.amount_cents / 100;
            const ppc = price / b.coins;
            const savePct = basePricePerCoin ? Math.max(0, Math.round((1 - ppc / basePricePerCoin) * 100)) : 0;
            const isSelected = selected === b.id;
            return (
              <div key={b.id} className={`relative rounded-2xl transition ring-1 ${isSelected ? "ring-brand-teal shadow-[0_10px_30px_rgba(8,145,178,0.25)]" : "ring-border/60"}`}>
                <button
                  onClick={() => setSelected(b.id)}
                  className={
                    "group relative overflow-hidden w-full rounded-2xl border border-border bg-card p-4 text-left shadow-sm transition " +
                    (b.id === "coins_500"
                      ? "before:absolute before:inset-0 before:rounded-2xl before:bg-[radial-gradient(ellipse_at_center,rgba(8,145,178,0.35),transparent_60%)] before:opacity-0 hover:before:opacity-100 before:transition-opacity"
                      : "")
                  }
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="grid size-12 place-items-center rounded-lg bg-amber-100 text-amber-700 ring-1 ring-amber-300">
                        <CoinStackIcon className="h-7 w-7" />
                      </div>
                      <div className="min-w-0">
                        <div className="truncate font-semibold">{b.name}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{b.coins} coins • ~${ppc.toFixed(3)}/coin</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="rounded-md bg-secondary px-2 py-1 text-sm font-semibold">${price.toFixed(2)}</div>
                      {savePct >= 5 && <div className="mt-1 text-emerald-600 text-xs font-semibold">Save {savePct}%</div>}
                    </div>
                  </div>
                  {isSelected && (
                    <span className="absolute top-2 right-2 rounded-full bg-brand-teal/20 p-1 text-brand-teal">
                      <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden>
                        <path fill="currentColor" d="M7.5 13.5L3.5 9.5l1.4-1.4 2.6 2.6 7-7 1.4 1.4z" />
                      </svg>
                    </span>
                  )}

                  {/* Sparkle shimmer overlay for Popular */}
                  {b.id === "coins_500" && (
                    <>
                      <Ribbon text="Popular" />
                      <span className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl">
                        <span
                          className="absolute top-0 left-0 h-full w-1/3 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-70"
                          style={{ animation: 'bundleShimmer 1.6s linear infinite' }}
                        />
                      </span>
                    </>
                  )}

                  {/* Gentle pulse for Best value */}
                  {b.id === "coins_2500" && <span className="animate-pulse"><Ribbon text="Best value" /></span>}
                </button>
              </div>
            );
          })}
        </div>

        <DialogFooter>
          <div className="mr-auto text-xs text-muted-foreground">
            {selectedBundle && (
              <>After purchase: <span className="font-semibold">{(user?.coinsBalance ?? 0) + (selectedBundle?.coins ?? 0)}</span> coins</>
            )}
          </div>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleBuy} disabled={!selected || loading} variant="brand-accent">
            {loading ? "Processing..." : selectedBundle ? `Buy ${selectedBundle.name} — $${(selectedBundle.amount_cents / 100).toFixed(2)}` : "Buy"}
          </Button>
        </DialogFooter>
    </SharedModal>
  );
};

export default BuyCreditsDialog;

