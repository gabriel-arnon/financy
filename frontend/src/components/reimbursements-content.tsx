"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, FileText, Pencil, Plus, RefreshCw, Search, Send, Trash2, UserPlus, X } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import {
  addReimbursementItem,
  cancelReimbursementClaim,
  createReimbursementClaim,
  createReimbursementContact,
  deleteReimbursementContact,
  deleteReimbursementItem,
  getFileSignedUrl,
  getReimbursementClaims,
  getReimbursementContacts,
  getReimbursementEligibleTransactions,
  getReimbursementEvents,
  getReimbursementOverview,
  getTransactionAttachments,
  refreshReimbursementSnapshots,
  sendReimbursementClaim,
  updateReimbursementClaim,
  updateReimbursementContact,
  updateReimbursementItem
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { getAccountName, getCardNameWithAccount, getCategoryName, isActiveEntity } from "@/lib/labels";
import type {
  Account,
  Card,
  Category,
  ReimbursementClaim,
  ReimbursementContact,
  ReimbursementEligibleTransaction,
  ReimbursementEvent,
  ReimbursementOverview,
  TransactionAttachment
} from "@/lib/types";

type Tab = "overview" | "claims" | "contacts";
type BusyAction = "contact" | "claim" | "item" | "send" | "cancel" | "refresh" | "attachment" | null;

interface ReimbursementsContentProps {
  initialAccounts: Account[];
  initialCards: Card[];
  initialCategories: Category[];
  initialClaims: ReimbursementClaim[];
  initialContacts: ReimbursementContact[];
  initialEligibleTransactions: ReimbursementEligibleTransaction[];
  initialOverview: ReimbursementOverview;
}

interface ContactFormState {
  id: string | null;
  display_name: string;
  email: string;
  phone: string;
}

interface ClaimFormState {
  id: string | null;
  contact_id: string;
  title: string;
  due_date: string;
  description: string;
}

interface ConfirmDialogState {
  title: string;
  description: string;
  confirmLabel: string;
  variant: "primary" | "danger";
  onConfirm: () => Promise<void>;
  details?: Array<{ label: string; value: string }>;
}

const emptyContactForm: ContactFormState = { id: null, display_name: "", email: "", phone: "" };
const emptyClaimForm: ClaimFormState = { id: null, contact_id: "", title: "", due_date: "", description: "" };
const visibleClaimStatuses = new Set(["draft", "sent", "canceled"]);

function amountToInput(value: string | number) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "";
  return amount.toFixed(2);
}

function claimStatusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: "Rascunho",
    sent: "Enviada",
    canceled: "Cancelada"
  };
  return labels[status] ?? status;
}

function eventLabel(eventType: string) {
  const labels: Record<string, string> = {
    claim_created: "Cobrança criada",
    claim_updated: "Cobrança atualizada",
    item_added: "Item adicionado",
    item_updated: "Item atualizado",
    item_removed: "Item removido",
    claim_snapshots_refreshed: "Snapshots atualizados",
    claim_sent: "Cobrança finalizada",
    claim_canceled: "Cobrança cancelada"
  };
  return labels[eventType] ?? "Evento registrado";
}

function snapshotText(snapshot: Record<string, unknown>, key: string) {
  const value = snapshot[key];
  return typeof value === "string" ? value : "";
}

function snapshotAmount(snapshot: Record<string, unknown>, key: string) {
  const value = snapshot[key];
  return typeof value === "string" || typeof value === "number" ? formatCurrency(value) : formatCurrency(0);
}

function isoDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function ReimbursementsContent({
  initialAccounts,
  initialCards,
  initialCategories,
  initialClaims,
  initialContacts,
  initialEligibleTransactions,
  initialOverview
}: ReimbursementsContentProps) {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("overview");
  const [accounts] = useState(initialAccounts);
  const [cards] = useState(initialCards);
  const [categories] = useState(initialCategories);
  const [contacts, setContacts] = useState(initialContacts);
  const [claims, setClaims] = useState(initialClaims);
  const [overview, setOverview] = useState(initialOverview);
  const [eligibleTransactions, setEligibleTransactions] = useState(initialEligibleTransactions);
  const [selectedClaimId, setSelectedClaimId] = useState(initialClaims[0]?.id ?? null);
  const [claimEvents, setClaimEvents] = useState<ReimbursementEvent[]>([]);
  const [contactForm, setContactForm] = useState<ContactFormState | null>(null);
  const [claimForm, setClaimForm] = useState<ClaimFormState | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const confirmCancelRef = useRef<HTMLButtonElement | null>(null);
  const [claimQuery, setClaimQuery] = useState("");
  const [contactQuery, setContactQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [contactFilter, setContactFilter] = useState("all");
  const [transactionQuery, setTransactionQuery] = useState("");
  const [itemAmounts, setItemAmounts] = useState<Record<string, string>>({});
  const [attachmentsByTransaction, setAttachmentsByTransaction] = useState<Record<string, TransactionAttachment[]>>({});

  const activeContacts = useMemo(() => contacts.filter(isActiveEntity), [contacts]);
  const selectedClaim = useMemo(() => claims.find((claim) => claim.id === selectedClaimId) ?? null, [claims, selectedClaimId]);
  const filteredClaims = useMemo(() => {
    const normalized = claimQuery.trim().toLowerCase();
    return claims.filter((claim) => {
      const matchesQuery = !normalized || [claim.title, claim.contact?.display_name ?? ""].join(" ").toLowerCase().includes(normalized);
      const matchesStatus = statusFilter === "all" || claim.status === statusFilter;
      const matchesContact = contactFilter === "all" || claim.contact_id === contactFilter;
      return visibleClaimStatuses.has(claim.status) && matchesQuery && matchesStatus && matchesContact;
    });
  }, [claimQuery, claims, contactFilter, statusFilter]);
  const filteredContacts = useMemo(() => {
    const normalized = contactQuery.trim().toLowerCase();
    return contacts.filter((contact) => {
      if (!isActiveEntity(contact)) return false;
      if (!normalized) return true;
      return [contact.display_name, contact.email ?? "", contact.phone ?? ""].join(" ").toLowerCase().includes(normalized);
    });
  }, [contactQuery, contacts]);
  const contactClaimCount = useMemo(() => {
    const counts = new Map<string, number>();
    claims.forEach((claim) => counts.set(claim.contact_id, (counts.get(claim.contact_id) ?? 0) + 1));
    return counts;
  }, [claims]);
  const visibleEligibleTransactions = useMemo(() => eligibleTransactions.filter((item) => item.eligible), [eligibleTransactions]);

  useEffect(() => {
    if (!confirmDialog) return;
    window.setTimeout(() => confirmCancelRef.current?.focus(), 0);
  }, [confirmDialog]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape" || busyAction !== null) return;
      if (confirmDialog) {
        setConfirmDialog(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [busyAction, confirmDialog]);

  async function reloadAll() {
    const [nextOverview, nextContacts, nextClaims, nextEligible] = await Promise.all([
      getReimbursementOverview(),
      getReimbursementContacts(),
      getReimbursementClaims(),
      getReimbursementEligibleTransactions({ q: transactionQuery, limit: 50 })
    ]);
    setOverview(nextOverview);
    setContacts(nextContacts);
    setClaims(nextClaims);
    setEligibleTransactions(nextEligible);
    if (selectedClaimId && !nextClaims.some((claim) => claim.id === selectedClaimId)) {
      setSelectedClaimId(nextClaims[0]?.id ?? null);
    }
  }

  useEffect(() => {
    let active = true;
    if (!selectedClaimId) {
      return;
    }
    getReimbursementEvents(selectedClaimId)
      .then((events) => {
        if (active) setClaimEvents(events);
      })
      .catch(() => {
        if (active) setClaimEvents([]);
      });
    return () => {
      active = false;
    };
  }, [selectedClaimId, claims]);

  async function run(action: BusyAction, callback: () => Promise<void>) {
    setBusyAction(action);
    try {
      await callback();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao processar ação.");
    } finally {
      setBusyAction(null);
    }
  }

  async function submitContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contactForm?.display_name.trim()) {
      toast.error("Informe o nome da pessoa.");
      return;
    }
    await run("contact", async () => {
      const payload = {
        display_name: contactForm.display_name.trim(),
        email: contactForm.email.trim() || null,
        phone: contactForm.phone.trim() || null
      };
      if (contactForm.id) {
        await updateReimbursementContact(contactForm.id, payload);
        toast.success("Pessoa atualizada.");
      } else {
        await createReimbursementContact(payload);
        toast.success("Pessoa cadastrada.");
      }
      setContactForm(null);
      await reloadAll();
    });
  }

  async function inactivateContact(contact: ReimbursementContact) {
    setConfirmDialog({
      title: "Inativar pessoa",
      description: "O historico das cobrancas sera preservado e essa pessoa deixara de aparecer como ativa.",
      confirmLabel: "Inativar pessoa",
      variant: "danger",
      details: [
        { label: "Pessoa", value: contact.display_name },
        { label: "Cobrancas associadas", value: String(contactClaimCount.get(contact.id) ?? 0) }
      ],
      onConfirm: async () => {
        await run("contact", async () => {
          await deleteReimbursementContact(contact.id);
          toast.danger("Pessoa inativada.");
          await reloadAll();
        });
      }
    });
  }

  async function submitClaim(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!claimForm?.contact_id || !claimForm.title.trim()) {
      toast.error("Escolha uma pessoa e informe o título.");
      return;
    }
    await run("claim", async () => {
      const payload = {
        contact_id: claimForm.contact_id,
        title: claimForm.title.trim(),
        due_date: claimForm.due_date || null,
        description: claimForm.description.trim() || null
      };
      const saved = claimForm.id ? await updateReimbursementClaim(claimForm.id, payload) : await createReimbursementClaim(payload);
      toast.success(claimForm.id ? "Cobrança atualizada." : "Cobrança criada.");
      setSelectedClaimId(saved.id);
      setClaimForm(null);
      setTab("claims");
      await reloadAll();
    });
  }

  async function searchEligibleTransactions() {
    await run("item", async () => {
      setEligibleTransactions(await getReimbursementEligibleTransactions({ q: transactionQuery, limit: 50 }));
    });
  }

  async function addItem(transaction: ReimbursementEligibleTransaction) {
    if (!selectedClaim || selectedClaim.status !== "draft") return;
    const amount = itemAmounts[transaction.id] || amountToInput(transaction.available_amount);
    await run("item", async () => {
      const updated = await addReimbursementItem(selectedClaim.id, { transaction_id: transaction.id, amount_requested: amount });
      setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
      setSelectedClaimId(updated.id);
      toast.success("Item adicionado.");
      await reloadAll();
    });
  }

  async function updateItemAmount(itemId: string, amount: string) {
    if (!selectedClaim) return;
    await run("item", async () => {
      const updated = await updateReimbursementItem(selectedClaim.id, itemId, { amount_requested: amount });
      setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
      toast.success("Valor atualizado.");
      await reloadAll();
    });
  }

  async function removeItem(itemId: string) {
    if (!selectedClaim) return;
    const item = selectedClaim.items.find((candidate) => candidate.id === itemId);
    setConfirmDialog({
      title: "Remover item",
      description: "O item sera removido do rascunho e o saldo ressarcivel da transacao voltara a ficar disponivel.",
      confirmLabel: "Remover item",
      variant: "danger",
      details: [
        { label: "Item", value: item ? snapshotText(item.transaction_snapshot, "description") || "Transacao" : "Transacao" },
        { label: "Valor", value: item ? formatCurrency(item.amount_requested) : formatCurrency(0) }
      ],
      onConfirm: async () => {
        await run("item", async () => {
          const updated = await deleteReimbursementItem(selectedClaim.id, itemId);
          setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
          toast.danger("Item removido.");
          await reloadAll();
        });
      }
    });
  }

  async function refreshSnapshots() {
    if (!selectedClaim) return;
    await run("refresh", async () => {
      const updated = await refreshReimbursementSnapshots(selectedClaim.id);
      setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
      toast.success("Snapshots atualizados.");
      await reloadAll();
    });
  }

  async function finalizeClaim() {
    if (!selectedClaim) return;
    setConfirmDialog({
      title: "Finalizar cobranca",
      description: "Esta etapa apenas finaliza a cobranca no Financy. Os snapshots serao congelados e a edicao nao ficara disponivel nesta versao.",
      confirmLabel: "Finalizar cobranca",
      variant: "primary",
      details: [
        { label: "Pessoa", value: selectedClaim.contact?.display_name ?? "Sem pessoa" },
        { label: "Itens", value: String(selectedClaim.items.length) },
        { label: "Total", value: formatCurrency(selectedClaim.total_amount) }
      ],
      onConfirm: async () => {
        await run("send", async () => {
          const updated = await sendReimbursementClaim(selectedClaim.id);
          setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
          toast.success("Cobranca finalizada no Financy.");
          await reloadAll();
        });
      }
    });
  }

  async function cancelClaim() {
    if (!selectedClaim) return;
    setConfirmDialog({
      title: "Cancelar cobranca",
      description: "Os itens e snapshots serao preservados no historico, mas deixarao de reservar saldo ressarcivel.",
      confirmLabel: "Cancelar cobranca",
      variant: "danger",
      details: [
        { label: "Pessoa", value: selectedClaim.contact?.display_name ?? "Sem pessoa" },
        { label: "Saldo liberado", value: formatCurrency(selectedClaim.total_amount) }
      ],
      onConfirm: async () => {
        await run("cancel", async () => {
          const updated = await cancelReimbursementClaim(selectedClaim.id);
          setClaims((current) => current.map((claim) => (claim.id === updated.id ? updated : claim)));
          toast.danger("Cobranca cancelada.");
          await reloadAll();
        });
      }
    });
  }

  async function openTransactionAttachments(transactionId: string) {
    await run("attachment", async () => {
      const cached = attachmentsByTransaction[transactionId] ?? await getTransactionAttachments(transactionId);
      setAttachmentsByTransaction((current) => ({ ...current, [transactionId]: cached }));
      if (cached.length === 0) {
        toast.info("Essa transação não possui comprovantes anexados.");
        return;
      }
      const signed = await getFileSignedUrl(cached[0].file_id);
      window.open(signed.url, "_blank", "noopener,noreferrer");
    });
  }

  function editContact(contact: ReimbursementContact) {
    setContactForm({
      id: contact.id,
      display_name: contact.display_name,
      email: contact.email ?? "",
      phone: contact.phone ?? ""
    });
  }

  function editClaim(claim: ReimbursementClaim) {
    setClaimForm({
      id: claim.id,
      contact_id: claim.contact_id,
      title: claim.title,
      due_date: claim.due_date ?? "",
      description: claim.description ?? ""
    });
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-mint">Ressarcimentos</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Cobranças a receber</h1>
          <p className="mt-2 text-sm text-stone-500">Organize despesas pagas por você e finalize cobranças sem compartilhar dados financeiros gerais.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <UiButton icon={<UserPlus className="h-4 w-4" />} onClick={() => setContactForm(emptyContactForm)} variant="secondary">
            Criar pessoa
          </UiButton>
          <UiButton icon={<Plus className="h-4 w-4" />} onClick={() => setClaimForm({ ...emptyClaimForm, contact_id: activeContacts[0]?.id ?? "" })} variant="primary">
            Criar cobrança
          </UiButton>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase text-stone-500">Total em enviadas</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(overview.total_sent)}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase text-stone-500">Rascunhos</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{overview.draft_count}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase text-stone-500">Finalizadas</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{overview.sent_count}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-stone-200">
        {[
          ["overview", "Visão geral"],
          ["claims", "Cobranças"],
          ["contacts", "Pessoas"]
        ].map(([value, label]) => (
          <button
            key={value}
            className={`border-b-2 px-3 py-2 text-sm font-semibold ${tab === value ? "border-mint text-mint" : "border-transparent text-stone-600 hover:text-ink"}`}
            onClick={() => setTab(value as Tab)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-ink">Cobranças recentes</h2>
            <div className="mt-3 grid gap-2">
              {overview.recent_claims.length === 0 ? (
                <p className="rounded-md bg-stone-50 p-4 text-sm text-stone-500">Nenhuma cobrança criada ainda.</p>
              ) : overview.recent_claims.map((claim) => (
                <button key={claim.id} className="rounded-md border border-stone-200 px-3 py-2 text-left transition hover:bg-stone-50" onClick={() => { setSelectedClaimId(claim.id); setTab("claims"); }} type="button">
                  <span className="block text-sm font-semibold text-ink">{claim.title}</span>
                  <span className="mt-1 block text-xs text-stone-500">{claim.contact?.display_name ?? "Sem pessoa"} · {formatCurrency(claim.total_amount)} · {claimStatusLabel(claim.status)}</span>
                </button>
              ))}
            </div>
          </section>
          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-ink">Rascunhos para concluir</h2>
            <div className="mt-3 grid gap-2">
              {overview.draft_claims.length === 0 ? (
                <p className="rounded-md bg-stone-50 p-4 text-sm text-stone-500">Nenhum rascunho pendente.</p>
              ) : overview.draft_claims.map((claim) => (
                <button key={claim.id} className="rounded-md border border-stone-200 px-3 py-2 text-left transition hover:bg-stone-50" onClick={() => { setSelectedClaimId(claim.id); setTab("claims"); }} type="button">
                  <span className="block text-sm font-semibold text-ink">{claim.title}</span>
                  <span className="mt-1 block text-xs text-stone-500">{claim.items.length} itens · {formatCurrency(claim.total_amount)}</span>
                </button>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {tab === "contacts" ? (
        <section className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-stone-100 p-4 sm:flex-row sm:items-end sm:justify-between">
            <label className="grid gap-1.5 text-sm font-medium text-ink">
              Buscar pessoa
              <input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" placeholder="Nome, e-mail ou telefone" value={contactQuery} onChange={(event) => setContactQuery(event.target.value)} />
            </label>
            <UiButton icon={<UserPlus className="h-4 w-4" />} onClick={() => setContactForm(emptyContactForm)} variant="primary">
              Nova pessoa
            </UiButton>
          </div>
          <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredContacts.length === 0 ? (
              <p className="rounded-md bg-stone-50 p-4 text-sm text-stone-500 md:col-span-2 xl:col-span-3">Nenhuma pessoa cadastrada.</p>
            ) : filteredContacts.map((contact) => (
              <article key={contact.id} className="rounded-lg border border-stone-200 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-base font-semibold text-ink">{contact.display_name}</h3>
                    <p className="mt-1 text-sm text-stone-500">{contact.email || "Sem e-mail"} · {contact.phone || "Sem telefone"}</p>
                    <p className="mt-2 text-xs text-stone-500">Acesso compartilhado ainda não configurado.</p>
                    <p className="mt-1 text-xs font-medium text-stone-600">{contactClaimCount.get(contact.id) ?? 0} cobranças associadas</p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <UiButton aria-label="Editar pessoa" className="h-9 w-9 px-0" icon={<Pencil className="h-4 w-4" />} onClick={() => editContact(contact)} size="sm" />
                    <UiButton aria-label="Inativar pessoa" className="h-9 w-9 px-0" icon={<Trash2 className="h-4 w-4" />} onClick={() => { void inactivateContact(contact); }} size="sm" variant="danger" />
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {tab === "claims" ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(26rem,0.9fr)]">
          <section className="rounded-lg border border-stone-200 bg-white shadow-sm">
            <div className="grid gap-3 border-b border-stone-100 p-4 md:grid-cols-[1fr_11rem_12rem_auto]">
              <label className="grid gap-1.5 text-sm font-medium text-ink">
                Buscar
                <input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" placeholder="Título ou pessoa" value={claimQuery} onChange={(event) => setClaimQuery(event.target.value)} />
              </label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">
                Status
                <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="all">Todos</option>
                  <option value="draft">Rascunho</option>
                  <option value="sent">Enviada</option>
                  <option value="canceled">Cancelada</option>
                </select>
              </label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">
                Pessoa
                <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={contactFilter} onChange={(event) => setContactFilter(event.target.value)}>
                  <option value="all">Todas</option>
                  {contacts.map((contact) => <option key={contact.id} value={contact.id}>{contact.display_name}</option>)}
                </select>
              </label>
              <UiButton className="self-end" icon={<Plus className="h-4 w-4" />} onClick={() => setClaimForm({ ...emptyClaimForm, contact_id: activeContacts[0]?.id ?? "" })} variant="primary">
                Nova
              </UiButton>
            </div>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full table-fixed divide-y divide-stone-200 text-sm">
                <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
                  <tr>
                    <th className="px-3 py-3">Cobrança</th>
                    <th className="px-3 py-3">Pessoa</th>
                    <th className="px-3 py-3">Total</th>
                    <th className="px-3 py-3">Status</th>
                    <th className="px-3 py-3">Vencimento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {filteredClaims.map((claim) => (
                    <tr key={claim.id} className={`cursor-pointer transition hover:bg-stone-50 ${selectedClaimId === claim.id ? "bg-emerald-50/60" : ""}`} onClick={() => setSelectedClaimId(claim.id)}>
                      <td className="px-3 py-3">
                        <p className="font-semibold text-ink">{claim.title}</p>
                        <p className="mt-1 text-xs text-stone-500">{claim.items.length} itens · criada em {formatDate(claim.created_at.slice(0, 10))}</p>
                      </td>
                      <td className="px-3 py-3 text-stone-700">{claim.contact?.display_name ?? "Sem pessoa"}</td>
                      <td className="px-3 py-3 font-semibold text-ink">{formatCurrency(claim.total_amount)}</td>
                      <td className="px-3 py-3">{claimStatusLabel(claim.status)}</td>
                      <td className="px-3 py-3 text-stone-600">{claim.due_date ? formatDate(claim.due_date) : "Sem vencimento"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="grid gap-2 p-4 md:hidden">
              {filteredClaims.map((claim) => (
                <button key={claim.id} className={`rounded-lg border p-3 text-left ${selectedClaimId === claim.id ? "border-mint bg-emerald-50" : "border-stone-200 bg-white"}`} onClick={() => setSelectedClaimId(claim.id)} type="button">
                  <span className="block font-semibold text-ink">{claim.title}</span>
                  <span className="mt-1 block text-sm text-stone-500">{claim.contact?.display_name ?? "Sem pessoa"} · {formatCurrency(claim.total_amount)} · {claimStatusLabel(claim.status)}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white shadow-sm">
            {selectedClaim ? (
              <div>
                <div className="border-b border-stone-100 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-mint">{selectedClaim.contact?.display_name ?? "Sem pessoa"}</p>
                      <h2 className="mt-1 text-xl font-semibold text-ink">{selectedClaim.title}</h2>
                      <p className="mt-2 text-sm text-stone-500">{claimStatusLabel(selectedClaim.status)} · {selectedClaim.items.length} itens · {formatCurrency(selectedClaim.total_amount)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedClaim.status === "draft" ? (
                        <>
                          <UiButton icon={<Pencil className="h-4 w-4" />} onClick={() => editClaim(selectedClaim)} size="sm">Editar</UiButton>
                          <UiButton icon={<RefreshCw className="h-4 w-4" />} onClick={() => { void refreshSnapshots(); }} size="sm" disabled={busyAction === "refresh"}>Atualizar snapshots</UiButton>
                          <UiButton icon={<Send className="h-4 w-4" />} onClick={() => { void finalizeClaim(); }} size="sm" variant="primary" disabled={selectedClaim.items.length === 0 || busyAction === "send"}>Finalizar cobrança</UiButton>
                        </>
                      ) : null}
                      {selectedClaim.status !== "canceled" ? (
                        <UiButton icon={<Trash2 className="h-4 w-4" />} onClick={() => { void cancelClaim(); }} size="sm" variant="danger" disabled={busyAction === "cancel"}>Cancelar</UiButton>
                      ) : null}
                    </div>
                  </div>
                  {selectedClaim.status === "sent" ? (
                    <p className="mt-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-900">Dados congelados no envio. Esta etapa não compartilha acesso com a pessoa.</p>
                  ) : null}
                </div>

                <div className="space-y-4 p-4">
                  <div className="grid gap-2">
                    {selectedClaim.items.length === 0 ? (
                      <p className="rounded-md bg-stone-50 p-4 text-sm text-stone-500">Nenhum item adicionado.</p>
                    ) : selectedClaim.items.map((item) => (
                      <article key={item.id} className="rounded-lg border border-stone-200 p-3">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div className="min-w-0">
                            <h3 className="font-semibold text-ink">{snapshotText(item.transaction_snapshot, "description") || "Transação"}</h3>
                            <p className="mt-1 text-sm text-stone-500">
                              {formatDate(snapshotText(item.transaction_snapshot, "transaction_date"))} · {getCategoryName(snapshotText(item.transaction_snapshot, "category_id") || null, categories)}
                            </p>
                            <p className="mt-1 text-sm text-stone-500">
                              Original {snapshotAmount(item.transaction_snapshot, "amount")} · Solicitado {formatCurrency(item.amount_requested)}
                            </p>
                            {item.snapshot_is_current === false ? (
                              <p className="mt-2 rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">A transação original mudou desde o snapshot.</p>
                            ) : null}
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            <UiButton icon={<FileText className="h-4 w-4" />} onClick={() => { void openTransactionAttachments(item.transaction_id); }} size="sm">Comprovante</UiButton>
                            {selectedClaim.status === "draft" ? (
                              <>
                                <input aria-label="Valor solicitado" className="h-9 w-28 rounded-md border border-stone-200 px-2 text-sm outline-none focus:border-mint" defaultValue={amountToInput(item.amount_requested)} onBlur={(event) => { if (event.target.value !== amountToInput(item.amount_requested)) void updateItemAmount(item.id, event.target.value); }} />
                                <UiButton aria-label="Remover item" className="h-9 w-9 px-0" icon={<Trash2 className="h-4 w-4" />} onClick={() => { void removeItem(item.id); }} size="sm" variant="danger" />
                              </>
                            ) : null}
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>

                  {selectedClaim.status === "draft" ? (
                    <section className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <label className="relative flex-1">
                          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-stone-400" />
                          <input className="h-10 w-full rounded-md border border-stone-200 pl-9 pr-3 text-sm outline-none focus:border-mint" placeholder="Buscar transações elegíveis" value={transactionQuery} onChange={(event) => setTransactionQuery(event.target.value)} />
                        </label>
                        <UiButton icon={<Search className="h-4 w-4" />} onClick={() => { void searchEligibleTransactions(); }} disabled={busyAction === "item"}>Buscar</UiButton>
                      </div>
                      <div className="mt-3 grid gap-2">
                        {visibleEligibleTransactions.length === 0 ? (
                          <p className="rounded-md bg-white p-3 text-sm text-stone-500">Nenhuma transação elegível encontrada.</p>
                        ) : visibleEligibleTransactions.slice(0, 8).map((transaction) => (
                          <div key={transaction.id} className="grid gap-2 rounded-md border border-stone-200 bg-white p-3 lg:grid-cols-[1fr_9rem_auto] lg:items-center">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-ink">{transaction.description}</p>
                              <p className="mt-1 text-xs text-stone-500">
                                {formatDate(transaction.transaction_date)} · {getCategoryName(transaction.category_id, categories)} · {transaction.card_id ? getCardNameWithAccount(transaction.card_id, cards, accounts) : getAccountName(transaction.account_id, accounts)}
                              </p>
                              <p className="mt-1 text-xs text-stone-500">Disponível {formatCurrency(transaction.available_amount)} de {formatCurrency(transaction.amount)}</p>
                            </div>
                            <input aria-label={`Valor para ${transaction.description}`} className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={itemAmounts[transaction.id] ?? amountToInput(transaction.available_amount)} onChange={(event) => setItemAmounts((current) => ({ ...current, [transaction.id]: event.target.value }))} />
                            <UiButton icon={<Plus className="h-4 w-4" />} onClick={() => { void addItem(transaction); }} variant="secondary" disabled={busyAction === "item"}>Adicionar</UiButton>
                          </div>
                        ))}
                      </div>
                    </section>
                  ) : null}

                  <section>
                    <h3 className="text-sm font-semibold text-ink">Timeline</h3>
                    <div className="mt-3 grid gap-2">
                      {claimEvents.length === 0 ? (
                        <p className="rounded-md bg-stone-50 p-3 text-sm text-stone-500">Nenhum evento registrado.</p>
                      ) : claimEvents.map((event) => (
                        <div key={event.id} className="flex gap-3 rounded-md border border-stone-200 px-3 py-2">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 text-mint" />
                          <div>
                            <p className="text-sm font-medium text-ink">{eventLabel(event.event_type)}</p>
                            <p className="mt-1 text-xs text-stone-500">Você · {isoDateTime(event.created_at)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                </div>
              </div>
            ) : (
              <div className="p-6 text-sm text-stone-500">Selecione uma cobrança para revisar os detalhes.</div>
            )}
          </section>
        </div>
      ) : null}

      {contactForm ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-4 sm:items-center">
          <form className="w-full max-w-lg rounded-lg border border-stone-200 bg-white shadow-2xl" onSubmit={submitContact}>
            <div className="flex items-center justify-between border-b border-stone-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-ink">{contactForm.id ? "Editar pessoa" : "Nova pessoa"}</h2>
              <button aria-label="Fechar" className="rounded-md p-2 text-stone-500 hover:bg-stone-100" onClick={() => setContactForm(null)} type="button"><X className="h-4 w-4" /></button>
            </div>
            <div className="grid gap-4 p-5">
              <label className="grid gap-1.5 text-sm font-medium text-ink">Nome<input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={contactForm.display_name} onChange={(event) => setContactForm({ ...contactForm, display_name: event.target.value })} required /></label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">E-mail<input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={contactForm.email} onChange={(event) => setContactForm({ ...contactForm, email: event.target.value })} /></label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">Telefone<input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={contactForm.phone} onChange={(event) => setContactForm({ ...contactForm, phone: event.target.value })} /></label>
            </div>
            <div className="grid gap-2 border-t border-stone-200 p-5 sm:grid-cols-2">
              <UiButton onClick={() => setContactForm(null)} variant="ghost">Cancelar</UiButton>
              <UiButton icon={<UserPlus className="h-4 w-4" />} type="submit" variant="primary" disabled={busyAction === "contact"}>{busyAction === "contact" ? "Salvando..." : "Salvar pessoa"}</UiButton>
            </div>
          </form>
        </div>
      ) : null}

      {claimForm ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-4 sm:items-center">
          <form className="w-full max-w-xl rounded-lg border border-stone-200 bg-white shadow-2xl" onSubmit={submitClaim}>
            <div className="flex items-center justify-between border-b border-stone-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-ink">{claimForm.id ? "Editar cobrança" : "Nova cobrança"}</h2>
              <button aria-label="Fechar" className="rounded-md p-2 text-stone-500 hover:bg-stone-100" onClick={() => setClaimForm(null)} type="button"><X className="h-4 w-4" /></button>
            </div>
            <div className="grid gap-4 p-5">
              <label className="grid gap-1.5 text-sm font-medium text-ink">Pessoa<select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={claimForm.contact_id} onChange={(event) => setClaimForm({ ...claimForm, contact_id: event.target.value })} required><option value="">Selecione</option>{activeContacts.map((contact) => <option key={contact.id} value={contact.id}>{contact.display_name}</option>)}</select></label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">Título<input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" value={claimForm.title} onChange={(event) => setClaimForm({ ...claimForm, title: event.target.value })} required /></label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">Vencimento<input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal outline-none focus:border-mint" type="date" value={claimForm.due_date} onChange={(event) => setClaimForm({ ...claimForm, due_date: event.target.value })} /></label>
              <label className="grid gap-1.5 text-sm font-medium text-ink">Descrição<textarea className="min-h-24 rounded-md border border-stone-200 px-3 py-2 text-sm font-normal outline-none focus:border-mint" value={claimForm.description} onChange={(event) => setClaimForm({ ...claimForm, description: event.target.value })} /></label>
            </div>
            <div className="grid gap-2 border-t border-stone-200 p-5 sm:grid-cols-2">
              <UiButton onClick={() => setClaimForm(null)} variant="ghost">Cancelar</UiButton>
              <UiButton icon={<Plus className="h-4 w-4" />} type="submit" variant="primary" disabled={busyAction === "claim"}>{busyAction === "claim" ? "Salvando..." : "Salvar cobrança"}</UiButton>
            </div>
          </form>
        </div>
      ) : null}

      {confirmDialog ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-4 sm:items-center">
          <div aria-labelledby="reimbursement-confirm-title" aria-modal="true" className="w-full max-w-lg rounded-lg border border-stone-200 bg-white p-5 shadow-2xl" role="dialog">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="reimbursement-confirm-title" className="text-lg font-semibold text-ink">{confirmDialog.title}</h2>
                <p className="mt-2 text-sm leading-6 text-stone-600">{confirmDialog.description}</p>
              </div>
              <button aria-label="Fechar" className="rounded-md p-2 text-stone-500 hover:bg-stone-100" onClick={() => setConfirmDialog(null)} type="button" disabled={busyAction !== null}>
                <X className="h-4 w-4" />
              </button>
            </div>
            {confirmDialog.details && confirmDialog.details.length > 0 ? (
              <dl className="mt-4 grid gap-2 rounded-md bg-stone-50 p-3 text-sm">
                {confirmDialog.details.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-3">
                    <dt className="text-stone-500">{item.label}</dt>
                    <dd className="text-right font-semibold text-ink">{item.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <UiButton ref={confirmCancelRef} onClick={() => setConfirmDialog(null)} variant="ghost" disabled={busyAction !== null}>
                Voltar
              </UiButton>
              <UiButton
                onClick={() => {
                  void confirmDialog.onConfirm().then(() => setConfirmDialog(null));
                }}
                variant={confirmDialog.variant}
                disabled={busyAction !== null}
              >
                {busyAction ? "Processando..." : confirmDialog.confirmLabel}
              </UiButton>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
