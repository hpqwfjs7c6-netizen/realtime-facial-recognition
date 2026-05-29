"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";

type ToastKind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  notify: (message: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast doit être utilisé dans <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, kind: ToastKind = "info") => {
      const id = Date.now() + Math.random();
      setToasts((t) => [...t, { id, kind, message }]);
      // Auto-dismiss 4s (toast-dismiss UX rule)
      setTimeout(() => dismiss(id), 4000);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      {/* aria-live polite : annoncé sans voler le focus (toast-accessibility) */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="fixed bottom-4 right-4 z-[1000] flex flex-col gap-2 w-80"
      >
        {toasts.map((t) => {
          const styles =
            t.kind === "error"
              ? "border-rose-500/40 bg-rose-950/80 text-rose-100"
              : t.kind === "success"
                ? "border-emerald-500/40 bg-emerald-950/80 text-emerald-100"
                : "border-slate-600/40 bg-slate-900/90 text-slate-100";
          const Icon = t.kind === "error" ? AlertTriangle : CheckCircle2;
          return (
            <div
              key={t.id}
              role={t.kind === "error" ? "alert" : "status"}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur-md ${styles}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="flex-1">{t.message}</span>
              <button
                onClick={() => dismiss(t.id)}
                aria-label="Fermer la notification"
                className="shrink-0 rounded p-0.5 text-slate-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
