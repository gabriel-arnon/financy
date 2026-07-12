"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { CheckCircle2, Info, Trash2, X, XCircle } from "lucide-react";
import { cn } from "@/lib/classnames";

type ToastType = "success" | "error" | "info" | "danger";

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  danger: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const toastStyles: Record<ToastType, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  error: "border-red-200 bg-red-50 text-red-900",
  danger: "border-red-200 bg-red-50 text-red-900",
  info: "border-stone-200 bg-white text-ink"
};

const iconStyles: Record<ToastType, string> = {
  success: "text-mint",
  error: "text-red-600",
  danger: "text-red-600",
  info: "text-stone-500"
};

function ToastIcon({ type }: { type: ToastType }) {
  const className = cn("mt-0.5 h-4 w-4 shrink-0", iconStyles[type]);
  if (type === "success") return <CheckCircle2 className={className} />;
  if (type === "error") return <XCircle className={className} />;
  if (type === "danger") return <Trash2 className={className} />;
  return <Info className={className} />;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextToastIdRef = useRef(1);

  const removeToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = nextToastIdRef.current;
    nextToastIdRef.current += 1;
    setToasts((current) => [...current.slice(-3), { id, type, message }]);
    window.setTimeout(() => removeToast(id), 4500);
  }, [removeToast]);

  const value = useMemo<ToastContextValue>(() => ({
    success: (message) => addToast("success", message),
    error: (message) => addToast("error", message),
    danger: (message) => addToast("danger", message),
    info: (message) => addToast("info", message)
  }), [addToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-[80] grid w-[calc(100%-2rem)] max-w-sm gap-2 md:right-6 md:top-6" role="region" aria-live="polite" aria-label="Notificações">
        {toasts.map((toast) => (
          <div key={toast.id} className={cn("flex items-start gap-3 rounded-lg border px-4 py-3 text-sm shadow-lg", toastStyles[toast.type])}>
            <ToastIcon type={toast.type} />
            <p className="min-w-0 flex-1 leading-5">{toast.message}</p>
            <button className="rounded-md p-1 text-current opacity-70 transition hover:bg-white/60 hover:opacity-100" type="button" aria-label="Fechar notificação" onClick={() => removeToast(toast.id)}>
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast deve ser usado dentro de ToastProvider.");
  }
  return context;
}
