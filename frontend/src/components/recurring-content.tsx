"use client";

import { FormEvent, useMemo, useState } from "react";
import { CheckCircle2, Clock, Pencil, Plus, Trash2 } from "lucide-react";
import { IconButton, UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createRecurringItem, deleteRecurringItem, getPlanningOverview, updateRecurringItem } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getAccountName, getCardNameWithAccount, getCategoryName } from "@/lib/labels";
import type { Account, Card, Category, PlanningOverview, RecurringItem, RecurringItemPayload, RecurringKind } from "@/lib/types";

const kindLabels: Record<RecurringKind, string> = {
  installment: "Parcelas",
  fixed_bill: "Contas fixas",
  subscription: "Assinaturas"
};

const emptyPayload: RecurringItemPayload = {
  name: "",
  kind: "fixed_bill",
  amount: "0",
  cadence: "monthly",
  category_id: null,
  account_id: null,
  card_id: null,
  start_date: null,
  end_date: null,
  next_due_date: null,
  status: "active",
  source: "manual",
  notes: null,
  metadata: {}
};

interface RecurringContentProps {
  initialOverview: PlanningOverview;
  categories: Category[];
  accounts: Account[];
  cards: Card[];
}

export function RecurringContent({ initialOverview, categories, accounts, cards }: RecurringContentProps) {
  const toast = useToast();
  const [overview, setOverview] = useState(initialOverview);
  const [activeKind, setActiveKind] = useState<RecurringKind>("installment");
  const [form, setForm] = useState<RecurringItemPayload>({ ...emptyPayload, kind: "installment" });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const recurringByKind = useMemo(() => overview.recurring_items.filter((item) => item.kind === activeKind), [activeKind, overview.recurring_items]);
  const suggestions = useMemo(() => overview.recurring_suggestions.filter((item) => item.kind === activeKind), [activeKind, overview.recurring_suggestions]);

  async function reload() {
    setOverview(await getPlanningOverview());
  }

  function startCreate(kind = activeKind) {
    setEditingId(null);
    setForm({ ...emptyPayload, kind });
    setShowForm(true);
  }

  function edit(item: RecurringItem) {
    setEditingId(item.id);
    setForm({
      name: item.name,
      kind: item.kind,
      amount: item.amount,
      cadence: item.cadence,
      category_id: item.category_id,
      account_id: item.account_id,
      card_id: item.card_id,
      start_date: item.start_date,
      end_date: item.end_date,
      next_due_date: item.next_due_date,
      status: "active",
      source: item.source,
      notes: item.notes,
      metadata: item.metadata
    });
    setShowForm(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = { ...form, amount: form.amount || "0", status: "active" as const };
      if (editingId) {
        await updateRecurringItem(editingId, payload);
        toast.success("Recorrente atualizado.");
      } else {
        await createRecurringItem(payload);
        toast.success("Recorrente cadastrado.");
      }
      setShowForm(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar recorrente.");
    }
  }

  async function confirmSuggestion(item: RecurringItem) {
    try {
      await createRecurringItem({
        name: item.name,
        kind: item.kind,
        amount: item.amount,
        cadence: item.cadence,
        category_id: item.category_id,
        account_id: item.account_id,
        card_id: item.card_id,
        start_date: item.start_date,
        end_date: item.end_date,
        next_due_date: item.next_due_date,
        status: "active",
        source: "ai_confirmed",
        notes: item.notes,
        metadata: item.metadata
      });
      toast.success("Sugestão confirmada.");
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao confirmar sugestao.");
    }
  }

  async function ignoreSuggestion(item: RecurringItem) {
    try {
      await createRecurringItem({
        name: item.name,
        kind: item.kind,
        amount: item.amount,
        cadence: item.cadence,
        category_id: item.category_id,
        account_id: item.account_id,
        card_id: item.card_id,
        start_date: item.start_date,
        end_date: item.end_date,
        next_due_date: item.next_due_date,
        status: "ignored",
        source: "ai_ignored",
        notes: item.notes,
        metadata: item.metadata
      });
      toast.success("Sugestão ignorada.");
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao ignorar sugestao.");
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Inativar este recorrente?")) return;
    try {
      await deleteRecurringItem(id);
      toast.danger("Recorrente inativado.");
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao inativar recorrente.");
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-mint">Planejamento</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Recorrentes</h1>
          <p className="mt-2 text-sm text-stone-500">Gerencie parcelas, contas fixas e assinaturas com cadastro manual e sugestoes por historico.</p>
        </div>
        <UiButton icon={<Plus className="h-4 w-4" />} onClick={() => startCreate()} variant="primary">Novo recorrente</UiButton>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(kindLabels) as RecurringKind[]).map((kind) => (
          <button key={kind} className={`rounded-md border px-3 py-2 text-sm font-medium ${activeKind === kind ? "border-mint bg-emerald-50 text-mint" : "border-stone-200 bg-white text-stone-700"}`} onClick={() => { setActiveKind(kind); setForm((current) => ({ ...current, kind })); }} type="button">
            {kindLabels[kind]}
          </button>
        ))}
      </div>

      {showForm ? (
        <form onSubmit={submit} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <div className="grid gap-3 md:grid-cols-4">
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Nome" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Valor" type="number" step="0.01" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={form.category_id ?? ""} onChange={(event) => setForm({ ...form, category_id: event.target.value || null })}>
              <option value="">Sem categoria</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" type="date" value={form.next_due_date ?? ""} onChange={(event) => setForm({ ...form, next_due_date: event.target.value || null })} />
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value as RecurringKind })}>
              {(Object.keys(kindLabels) as RecurringKind[]).map((kind) => <option key={kind} value={kind}>{kindLabels[kind]}</option>)}
            </select>
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={form.account_id ?? ""} onChange={(event) => setForm({ ...form, account_id: event.target.value || null, card_id: null })}>
              <option value="">Sem conta</option>
              {accounts.map((account) => <option key={account.id} value={account.id}>{getAccountName(account.id, accounts)}</option>)}
            </select>
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={form.card_id ?? ""} onChange={(event) => setForm({ ...form, card_id: event.target.value || null, account_id: null })}>
              <option value="">Sem cartao</option>
              {cards.map((card) => <option key={card.id} value={card.id}>{getCardNameWithAccount(card.id, cards, accounts)}</option>)}
            </select>
            <div className="flex gap-2">
              <UiButton className="flex-1" type="submit" variant="primary">{editingId ? "Salvar" : "Criar"}</UiButton>
              <UiButton onClick={() => setShowForm(false)} type="button" variant="secondary">Cancelar</UiButton>
            </div>
          </div>
        </form>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-4 py-3">
            <h2 className="font-semibold text-ink">{kindLabels[activeKind]} confirmadas</h2>
          </div>
          <div className="divide-y divide-stone-100">
            {recurringByKind.map((item) => <RecurringRow key={item.id} item={item} categories={categories} accounts={accounts} cards={cards} onEdit={edit} onRemove={remove} />)}
            {recurringByKind.length === 0 ? <p className="px-4 py-8 text-center text-sm text-stone-500">Nenhum recorrente confirmado nesta aba.</p> : null}
          </div>
        </div>
        <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-4 py-3">
            <h2 className="font-semibold text-ink">Sugestões da IA</h2>
          </div>
          <div className="divide-y divide-stone-100">
            {suggestions.map((item) => (
              <div key={item.id} className="space-y-2 px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink">{item.name}</p>
                    <p className="text-sm text-stone-500">{formatCurrency(item.amount)} · {item.linked_transaction_count} ocorrencias</p>
                  </div>
                  <div className="flex gap-2">
                    <UiButton icon={<CheckCircle2 className="h-4 w-4" />} onClick={() => confirmSuggestion(item)} size="sm" variant="secondary">Confirmar</UiButton>
                    <UiButton onClick={() => ignoreSuggestion(item)} size="sm" variant="ghost">Ignorar</UiButton>
                  </div>
                </div>
                <p className="text-xs text-stone-500">{item.notes}</p>
              </div>
            ))}
            {suggestions.length === 0 ? <p className="px-4 py-8 text-center text-sm text-stone-500">Nenhuma sugestão para esta aba.</p> : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function RecurringRow({ item, categories, accounts, cards, onEdit, onRemove }: { item: RecurringItem; categories: Category[]; accounts: Account[]; cards: Card[]; onEdit: (item: RecurringItem) => void; onRemove: (id: string) => void }) {
  const origin = item.card_id ? getCardNameWithAccount(item.card_id, cards, accounts) : getAccountName(item.account_id, accounts);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <p className="truncate font-medium text-ink">{item.name}</p>
        <p className="mt-1 text-sm text-stone-500">{getCategoryName(item.category_id, categories)} · {origin}</p>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <p className="font-semibold text-ink">{formatCurrency(item.amount)}</p>
          <p className="inline-flex items-center gap-1 text-xs text-stone-500"><Clock className="h-3 w-3" /> {item.next_due_date || "Sem vencimento"}</p>
        </div>
        <IconButton aria-label="Editar recorrente" icon={<Pencil className="h-4 w-4" />} onClick={() => onEdit(item)} title="Editar" variant="secondary" />
        <IconButton aria-label="Inativar recorrente" icon={<Trash2 className="h-4 w-4" />} onClick={() => onRemove(item.id)} title="Inativar" variant="danger" />
      </div>
    </div>
  );
}
