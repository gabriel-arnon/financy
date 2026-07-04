"use client";

import { useEffect } from "react";
import { RefreshCcw } from "lucide-react";

interface GlobalErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalErrorPage({ error, reset }: GlobalErrorPageProps) {
  useEffect(() => {
    console.error("Falha global inesperada.", error);
  }, [error]);

  return (
    <html lang="pt-BR">
      <body>
        <main className="min-h-screen bg-paper px-4 py-8 text-ink">
          <section className="mx-auto max-w-2xl rounded-lg border border-red-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-medium text-red-700">Erro crítico</p>
            <h1 className="mt-2 text-2xl font-semibold">Não foi possível iniciar o Financy.</h1>
            <p className="mt-3 text-sm leading-6 text-stone-600">
              Tente novamente. Se o problema continuar, confira os logs do frontend e a disponibilidade da API.
            </p>
            <button
              className="mt-5 inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-mint px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700"
              type="button"
              onClick={reset}
            >
              <RefreshCcw className="h-4 w-4" />
              Tentar novamente
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
