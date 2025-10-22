import React from "react";

export const LoadingOverlay: React.FC<{ show: boolean; label?: string }>= ({ show, label }) => {
  if (!show) return null;
  return (
    <div className="fixed inset-0 z-[70] grid place-items-center bg-black/60 backdrop-blur-sm">
      <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-2 shadow-md animate-in fade-in zoom-in-95">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-brand-orange" />
        <span className="text-sm text-foreground">{label ?? "Loading"}</span>
      </div>
    </div>
  );
};

