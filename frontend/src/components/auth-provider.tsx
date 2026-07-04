"use client";

import type { Session } from "@supabase/supabase-js";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";

interface AuthContextValue {
  configured: boolean;
  loading: boolean;
  session: Session | null;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function writeSessionCookie(session: Session | null) {
  if (!session?.access_token) {
    document.cookie = "financy_access_token=; Path=/; Max-Age=0; SameSite=Lax";
    return;
  }
  document.cookie = `financy_access_token=${session.access_token}; Path=/; Max-Age=${60 * 60}; SameSite=Lax`;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const configured = isSupabaseConfigured();
  const supabase = getSupabaseClient();
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(() => configured);

  useEffect(() => {
    if (!configured || !supabase) {
      return;
    }

    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      writeSessionCookie(data.session);
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      writeSessionCookie(nextSession);
      if (!nextSession && pathname !== "/login") {
        router.replace("/login");
      }
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, [configured, pathname, router, supabase]);

  useEffect(() => {
    if (!configured || loading) return;
    if (!session && pathname !== "/login") {
      router.replace("/login");
    }
    if (session && pathname === "/login") {
      router.replace("/");
    }
  }, [configured, loading, pathname, router, session]);

  const value = useMemo<AuthContextValue>(
    () => ({
      configured,
      loading,
      session,
      signOut: async () => {
        writeSessionCookie(null);
        await supabase?.auth.signOut();
        setSession(null);
        router.replace("/login");
      }
    }),
    [configured, loading, router, session, supabase]
  );

  if (configured && loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper px-4 text-sm text-stone-500">
        Carregando sessao...
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
