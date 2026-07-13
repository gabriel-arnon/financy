"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, FileText } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import {
  acknowledgeGuestReimbursementClaim,
  disputeGuestReimbursementClaim,
  getGuestReimbursementClaimAttachmentSignedUrl,
  getGuestReimbursementClaimAttachments
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import type { GuestReimbursementClaim, ReimbursementClaimAttachment } from "@/lib/types";

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    sent: "Enviada",
    acknowledged: "Reconhecida",
    disputed: "Contestada",
    canceled: "Cancelada",
  };
  return labels[status] ?? status;
}

export function GuestReimbursementsContent({ initialClaims }: { initialClaims: GuestReimbursementClaim[] }) {
  const toast = useToast();
  const [claims, setClaims] = useState(initialClaims);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [attachmentsByClaim, setAttachmentsByClaim] = useState<Record<string, ReimbursementClaimAttachment[]>>({});

  async function run(claimId: string, callback: () => Promise<GuestReimbursementClaim>, success: string) {
    setBusyId(claimId);
    try {
      const updated = await callback();
      setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
      toast.success(success);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao processar ação.");
    } finally {
      setBusyId(null);
    }
  }

  async function openAttachment(claimId: string, attachment: ReimbursementClaimAttachment) {
    setBusyId(claimId);
    try {
      const signed = await getGuestReimbursementClaimAttachmentSignedUrl(claimId, attachment.id);
      window.open(signed.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao abrir comprovante.");
    } finally {
      setBusyId(null);
    }
  }

  async function loadAttachments(claimId: string) {
    setBusyId(claimId);
    try {
      const attachments = await getGuestReimbursementClaimAttachments(claimId);
      setAttachmentsByClaim((current) => ({ ...current, [claimId]: attachments }));
      if (attachments.length === 0) toast.info("Nenhum comprovante compartilhado.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao carregar comprovantes.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">Portal de ressarcimentos</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Cobranças compartilhadas</h1>
        <p className="mt-2 text-sm text-stone-500">Visualize apenas as cobranças destinadas a você.</p>
      </div>
      <div className="grid gap-3">
        {claims.length === 0 ? (
          <div className="rounded-lg border border-stone-200 bg-white p-6 text-sm text-stone-500 shadow-sm">Nenhuma cobrança compartilhada no momento.</div>
        ) : claims.map((claim) => (
          <article key={claim.id} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-mint">Ressarcimento</p>
                <h2 className="mt-1 text-lg font-semibold text-ink">{claim.title}</h2>
                <p className="mt-1 text-sm text-stone-500">
                  {statusLabel(claim.status)} · {claim.items.length} itens{claim.due_date ? ` · vence em ${formatDate(claim.due_date)}` : ""}
                </p>
              </div>
              <p className="text-xl font-semibold text-ink">{formatCurrency(claim.total_amount)}</p>
            </div>
            <div className="mt-4 grid gap-2">
              {claim.items.map((item) => (
                <div key={item.id} className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-700">
                  <span className="font-medium text-ink">{item.description}</span>
                  <span className="ml-2">{formatCurrency(item.amount_requested)}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-md border border-stone-200 bg-stone-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-ink">Comprovantes compartilhados</p>
                <UiButton icon={<FileText className="h-4 w-4" />} onClick={() => { void loadAttachments(claim.id); }} size="sm" disabled={busyId === claim.id}>
                  Ver comprovantes
                </UiButton>
              </div>
              {attachmentsByClaim[claim.id]?.length ? (
                <div className="mt-3 grid gap-2">
                  {attachmentsByClaim[claim.id].map((attachment) => (
                    <button key={attachment.id} className="rounded-md bg-white px-3 py-2 text-left text-sm text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50" onClick={() => { void openAttachment(claim.id, attachment); }} type="button">
                      {attachment.file.original_filename}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            {claim.status === "sent" || claim.status === "acknowledged" || claim.status === "disputed" ? (
              <div className="mt-4 flex flex-wrap gap-2">
                <UiButton
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  onClick={() => { void run(claim.id, () => acknowledgeGuestReimbursementClaim(claim.id), "Cobrança reconhecida."); }}
                  variant="primary"
                  disabled={busyId === claim.id}
                >
                  Reconhecer
                </UiButton>
                <UiButton
                  icon={<AlertTriangle className="h-4 w-4" />}
                  onClick={() => { void run(claim.id, () => disputeGuestReimbursementClaim(claim.id, "Contestada pelo portal."), "Cobrança contestada."); }}
                  variant="danger"
                  disabled={busyId === claim.id}
                >
                  Contestar
                </UiButton>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
