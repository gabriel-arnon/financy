"use client";

import { LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export function AuthStatus() {
  const { configured, session, signOut } = useAuth();

  if (!configured) {
    return (
      <div className="absolute bottom-6 left-5 right-5 rounded-lg border border-stone-200 bg-stone-50 p-4">
        <p className="text-sm font-medium text-ink">MVP local</p>
        <p className="mt-1 text-xs leading-5 text-stone-500">Auth real aguardando envs Supabase. Modo local usa bypass controlado.</p>
      </div>
    );
  }

  return (
    <div className="absolute bottom-6 left-5 right-5 rounded-lg border border-stone-200 bg-stone-50 p-4">
      <div className="flex items-start gap-2">
        <ShieldCheck className="mt-0.5 h-4 w-4 text-mint" />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-ink">{session?.user.email ?? "Usuario autenticado"}</p>
          <button className="mt-3 inline-flex items-center gap-2 text-xs font-medium text-stone-600 hover:text-coral" onClick={signOut} type="button">
            <LogOut className="h-3.5 w-3.5" />
            Sair
          </button>
        </div>
      </div>
    </div>
  );
}
