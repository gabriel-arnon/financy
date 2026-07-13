"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { acceptReimbursementInvitation } from "@/lib/api";

export function AcceptReimbursementInvitationContent({ token }: { token: string }) {
  const [status, setStatus] = useState<"loading" | "success" | "error">(token ? "loading" : "error");
  const [message, setMessage] = useState(token ? "Validando convite..." : "Convite inválido ou ausente.");

  useEffect(() => {
    if (!token) return;
    let active = true;
    acceptReimbursementInvitation(token)
      .then(() => {
        if (!active) return;
        setStatus("success");
        setMessage("Acesso liberado para as cobranças compartilhadas.");
      })
      .catch((err) => {
        if (!active) return;
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Não foi possível aceitar o convite.");
      });
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <section className="mx-auto max-w-lg rounded-lg border border-stone-200 bg-white p-6 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-stone-50">
        {status === "loading" ? <Loader2 className="h-5 w-5 animate-spin text-mint" /> : null}
        {status === "success" ? <CheckCircle2 className="h-5 w-5 text-mint" /> : null}
        {status === "error" ? <XCircle className="h-5 w-5 text-red-600" /> : null}
      </div>
      <h1 className="mt-4 text-xl font-semibold text-ink">Convite de ressarcimento</h1>
      <p className="mt-2 text-sm leading-6 text-stone-600">{message}</p>
      <div className="mt-5">
        <Link className="inline-flex min-h-10 items-center justify-center rounded-md border border-transparent bg-mint px-4 py-2 text-sm font-medium leading-none text-white shadow-sm transition hover:bg-emerald-700" href="/guest/reimbursements">
          Abrir portal
        </Link>
      </div>
    </section>
  );
}
