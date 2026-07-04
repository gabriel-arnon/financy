"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const configured = isSupabaseConfigured();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const supabase = getSupabaseClient();
    if (!supabase) {
      setError("Supabase Auth nao esta configurado.");
      return;
    }

    setLoading(true);
    setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (signInError) {
      setError(signInError.message);
      return;
    }
    router.replace("/");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4 py-10">
      <section className="w-full max-w-sm rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-mint text-base font-semibold text-white">F</span>
          <div>
            <h1 className="text-xl font-semibold text-ink">Entrar no Financy</h1>
            <p className="mt-1 text-sm text-stone-500">Acesse seu ambiente financeiro.</p>
          </div>
        </div>

        {!configured ? (
          <p className="mt-5 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Configure `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` para habilitar login real.
          </p>
        ) : null}

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-stone-600">Email</span>
            <input
              className="h-11 w-full rounded-md border border-stone-200 px-3 text-sm outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-stone-600">Senha</span>
            <input
              className="h-11 w-full rounded-md border border-stone-200 px-3 text-sm outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <p className="text-sm text-coral">{error}</p> : null}
          <button
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-mint px-4 text-sm font-medium text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!configured || loading}
            type="submit"
          >
            <LogIn className="h-4 w-4" />
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
