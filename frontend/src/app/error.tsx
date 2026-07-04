"use client";

import { useEffect } from "react";
import { RefreshCcw } from "lucide-react";
import { UiButton } from "@/components/ui-button";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("Falha inesperada na interface.", error);
  }, [error]);

  return (
    <section className="rounded-lg border border-red-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-red-700">Erro inesperado</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink">Não foi possível carregar esta área.</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
        Tente novamente. Se o erro continuar, verifique a conexão com a API e os dados carregados nesta tela.
      </p>
      <UiButton className="mt-5" icon={<RefreshCcw className="h-4 w-4" />} onClick={reset} variant="primary">
        Tentar novamente
      </UiButton>
    </section>
  );
}
