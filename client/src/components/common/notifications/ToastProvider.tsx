import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

interface Toast { id: string; title?: string; message: string; tone?: "success" | "error" | "info"; }

interface ToastContextType {
  toasts: Toast[];
  push: (toast: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToasts = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToasts must be used within ToastProvider");
  return ctx;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: string) => setToasts((ts) => ts.filter((t) => t.id !== id)), []);
  const push = useCallback((toast: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((ts) => [...ts, { id, ...toast }]);
    const timeout = toast.tone === "error" ? 8000 : 3500;
    setTimeout(() => remove(id), timeout);
  }, [remove]);

  const value = useMemo(() => ({ toasts, push, remove }), [toasts, push, remove]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-80 flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={cn(
            "pointer-events-auto rounded-md border p-3 shadow bg-card",
            t.tone === "success" && "border-brand-lime/60",
            t.tone === "error" && "border-red-500/60",
            t.tone === "info" && "border-brand-blue/60",
          )}>
            {t.title && <div className="text-sm font-semibold">{t.title}</div>}
            <div className="text-sm text-muted-foreground">{t.message}</div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

