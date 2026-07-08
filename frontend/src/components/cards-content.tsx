"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, CreditCard, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { NavigatingLink } from "@/components/navigating-link";
import { IconButton, UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createCard, deleteCard, getAccounts, getCards, getStatements, updateCard } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { formatAccountName, isActiveEntity } from "@/lib/labels";
import type { Account, Card, CardPayload, CardStatementSummary } from "@/lib/types";

const emptyCard: CardPayload = {
  account_id: null,
  name: "",
  institution: "",
  brand: "",
  last_digits: "",
  limit_amount: "",
  closing_day: null,
  due_day: null,
  status: "active"
};

interface CardsContentProps {
  initialAccounts: Account[];
  initialCards: Card[];
  initialStatements: CardStatementSummary[];
}

function toOptionalNumber(value: string): number | null {
  const text = value.trim();
  return text ? Number(text) : null;
}

function statementAmount(statement: CardStatementSummary): number {
  return Number(statement.reported_total ?? statement.calculated_total ?? 0);
}

function isOpenStatement(statement: CardStatementSummary): boolean {
  return statement.status === "open" || statement.status === "overdue";
}

export function CardsContent({ initialAccounts, initialCards, initialStatements }: CardsContentProps) {
  const toast = useToast();
  const [accounts, setAccounts] = useState<Account[]>(initialAccounts);
  const [cards, setCards] = useState<Card[]>(initialCards);
  const [statements, setStatements] = useState<CardStatementSummary[]>(initialStatements);
  const [cardForm, setCardForm] = useState<CardPayload>(emptyCard);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [showCardForm, setShowCardForm] = useState(false);

  const activeAccounts = useMemo(() => accounts.filter(isActiveEntity), [accounts]);
  const activeCards = useMemo(() => cards.filter(isActiveEntity), [cards]);
  const openStatementsByCard = useMemo(() => {
    return statements.filter(isOpenStatement).reduce<Record<string, { count: number; total: number }>>((summary, statement) => {
      const current = summary[statement.card_id] ?? { count: 0, total: 0 };
      summary[statement.card_id] = {
        count: current.count + 1,
        total: current.total + statementAmount(statement)
      };
      return summary;
    }, {});
  }, [statements]);
  const cardSummary = useMemo(() => {
    return activeCards.reduce(
      (summary, card) => {
        const limit = Number(card.limit_amount ?? 0);
        const used = openStatementsByCard[card.id]?.total ?? 0;
        summary.totalLimit += Number.isFinite(limit) ? limit : 0;
        summary.totalUsed += used;
        return summary;
      },
      { totalLimit: 0, totalUsed: 0 }
    );
  }, [activeCards, openStatementsByCard]);
  const totalAvailable = Math.max(cardSummary.totalLimit - cardSummary.totalUsed, 0);

  async function loadData() {
    const [nextAccounts, nextCards, nextStatements] = await Promise.all([getAccounts(), getCards(), getStatements()]);
    setAccounts(nextAccounts);
    setCards(nextCards);
    setStatements(nextStatements);
  }

  useEffect(() => {
    let active = true;
    Promise.all([getAccounts(), getCards(), getStatements()])
      .then(([nextAccounts, nextCards, nextStatements]) => {
        if (!active) return;
        setAccounts(nextAccounts);
        setCards(nextCards);
        setStatements(nextStatements);
      })
      .catch((err) => {
        if (active && initialCards.length === 0) toast.error(err instanceof Error ? err.message : "Falha ao carregar cartões.");
      });
    return () => {
      active = false;
    };
  }, [initialCards.length, toast]);

  async function handleCardSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload: CardPayload = {
        ...cardForm,
        account_id: cardForm.account_id || null,
        institution: cardForm.institution || null,
        brand: cardForm.brand || null,
        limit_amount: cardForm.limit_amount || null,
        closing_day: toOptionalNumber(String(cardForm.closing_day ?? "")),
        due_day: toOptionalNumber(String(cardForm.due_day ?? "")),
        status: "active"
      };
      if (editingCardId) {
        await updateCard(editingCardId, payload);
        toast.success("Cartão atualizado.");
      } else {
        await createCard(payload);
        toast.success("Cartão cadastrado.");
      }
      setCardForm(emptyCard);
      setEditingCardId(null);
      setShowCardForm(false);
      await loadData();
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Falha ao salvar cartão.";
      toast.error(messageText);
    }
  }

  function editCard(card: Card) {
    setEditingCardId(card.id);
    setShowCardForm(true);
    setCardForm({
      account_id: card.account_id,
      name: card.name,
      institution: card.institution ?? "",
      brand: card.brand ?? "",
      last_digits: card.last_digits,
      limit_amount: card.limit_amount ?? "",
      closing_day: card.closing_day,
      due_day: card.due_day,
      status: "active"
    });
  }

  async function inactivateCard(cardId: string) {
    if (!window.confirm("Inativar este cartão? Ele não aparecerá mais nas listagens.")) return;
    try {
      await deleteCard(cardId);
      toast.danger("Cartão inativado.");
      await loadData();
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Falha ao inativar cartão.";
      toast.error(messageText);
    }
  }

  function cancelCardEdit() {
    setEditingCardId(null);
    setCardForm(emptyCard);
    setShowCardForm(false);
  }

  function startNewCard() {
    setEditingCardId(null);
    setCardForm(emptyCard);
    setShowCardForm(true);
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-mint">Crédito</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Cartões de Crédito</h1>
          <p className="mt-2 text-sm text-stone-500">Gerencie cartões como entidades financeiras próprias, vinculadas a contas bancárias e faturas.</p>
        </div>
        <UiButton icon={<Plus className="h-4 w-4" />} onClick={startNewCard} variant="primary">
          Novo cartão
        </UiButton>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Total de cartões</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{activeCards.length}</p>
        </div>
        <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Limite total</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(cardSummary.totalLimit)}</p>
        </div>
        <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Total utilizado</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(cardSummary.totalUsed)}</p>
        </div>
        <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Disponível</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(totalAvailable)}</p>
        </div>
      </div>

      {showCardForm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/55 px-4 py-6 backdrop-blur-sm">
          <form onSubmit={handleCardSubmit} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-lg border border-stone-200 bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone-200 px-5 py-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
                <CreditCard className="h-5 w-5 text-mint" />
                {editingCardId ? "Editar cartão de crédito" : "Novo cartão de crédito"}
              </h2>
              <button
                aria-label="Fechar formulário"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-ink"
                onClick={cancelCardEdit}
                type="button"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 px-5 py-5">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Nome</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Nome do cartão" value={cardForm.name} onChange={(event) => setCardForm({ ...cardForm, name: event.target.value })} required />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Instituição</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Banco ou emissor" value={cardForm.institution ?? ""} onChange={(event) => setCardForm({ ...cardForm, institution: event.target.value })} />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-ink">Bandeira</span>
                  <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Ex: Elo" value={cardForm.brand ?? ""} onChange={(event) => setCardForm({ ...cardForm, brand: event.target.value })} />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-ink">Últimos 4 dígitos</span>
                  <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Ex: 6149" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} value={cardForm.last_digits} onChange={(event) => setCardForm({ ...cardForm, last_digits: event.target.value.replace(/\D/g, "").slice(0, 4) })} required />
                </label>
              </div>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Conta vinculada</span>
                <select className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={cardForm.account_id ?? ""} onChange={(event) => setCardForm({ ...cardForm, account_id: event.target.value || null })}>
                  <option value="">Sem conta vinculada</option>
                  {activeAccounts.map((account) => <option key={account.id} value={account.id}>{formatAccountName(account)}</option>)}
                </select>
              </label>
              {activeAccounts.length === 0 ? (
                <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  <p>Você pode criar o cartão agora e vincular uma conta depois.</p>
                  <Link href="/accounts" className="mt-2 inline-flex font-medium text-amber-900 underline underline-offset-2">
                    Criar conta bancária
                  </Link>
                </div>
              ) : null}
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Limite do cartão</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="R$ 0,00" type="number" step="0.01" value={cardForm.limit_amount ?? ""} onChange={(event) => setCardForm({ ...cardForm, limit_amount: event.target.value })} />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Dia de vencimento</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="1-31" type="number" min={1} max={31} value={cardForm.due_day ?? ""} onChange={(event) => setCardForm({ ...cardForm, due_day: event.target.value ? Number(event.target.value) : null })} />
              </label>
            </div>

            <div className="grid gap-2 border-t border-stone-200 px-5 py-4 sm:grid-cols-2">
              <UiButton onClick={cancelCardEdit} variant="secondary">
                Cancelar
              </UiButton>
              <UiButton icon={editingCardId ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
                {editingCardId ? "Salvar" : "Criar"}
              </UiButton>
            </div>
          </form>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full table-fixed divide-y divide-stone-200 text-sm">
            <colgroup>
              <col className="w-[24%]" />
              <col className="w-[24%]" />
              <col className="w-[13%]" />
              <col className="w-[14%]" />
              <col className="w-[10%]" />
              <col className="w-[15%]" />
            </colgroup>
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="px-3 py-3">Cartão</th>
                <th className="px-3 py-3">Conta vinculada</th>
                <th className="px-3 py-3">Limite</th>
                <th className="px-3 py-3">Faturas abertas</th>
                <th className="px-3 py-3">Utilização</th>
                <th className="px-3 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {activeCards.map((card) => {
                const openSummary = openStatementsByCard[card.id] ?? { count: 0, total: 0 };
                const limit = card.limit_amount ? Number(card.limit_amount) : null;
                const usagePercent = limit && limit > 0 ? Math.min((openSummary.total / limit) * 100, 999) : null;
                const linkedAccount = accounts.find((account) => account.id === card.account_id);
                return (
                  <tr key={card.id} className="align-middle">
                    <td className="px-3 py-2.5">
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <p className="truncate font-medium text-ink" title={card.name}>{card.name}</p>
                          <span className="shrink-0 rounded-md bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-700">••••{card.last_digits}</span>
                        </div>
                        <p className="mt-1 truncate text-xs text-stone-500">{card.brand ? `Bandeira ${card.brand}` : "Bandeira não informada"}</p>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-stone-600">
                      <div className="min-w-0">
                        {linkedAccount ? (
                          <Link href={`/accounts/${linkedAccount.id}`} className="line-clamp-2 font-medium text-stone-700 hover:text-mint">
                            {formatAccountName(linkedAccount)}
                          </Link>
                        ) : (
                          <p className="line-clamp-2 font-medium text-stone-700">Sem conta</p>
                        )}
                        <p className="mt-1 text-xs text-stone-400">Conta vinculada</p>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-stone-600">{card.limit_amount ? formatCurrency(card.limit_amount) : "Não informado"}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-stone-600">
                      <span className="font-medium text-stone-700">{openSummary.count}</span>
                      <span className="text-stone-400"> · </span>
                      {formatCurrency(openSummary.total)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-stone-600">{usagePercent === null ? "Indisponível" : `${usagePercent.toFixed(2)}%`}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center justify-end gap-1.5">
                        <NavigatingLink href={`/cards/${card.id}`} className="inline-flex h-8 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-stone-300 bg-white px-2.5 text-xs font-medium text-ink shadow-sm hover:bg-stone-50">
                          Ver cartão
                          <ArrowRight className="h-3.5 w-3.5 shrink-0" />
                        </NavigatingLink>
                        <IconButton aria-label="Editar cartão" icon={<Pencil className="h-4 w-4" />} onClick={() => editCard(card)} title="Editar" variant="secondary" />
                        <IconButton aria-label="Inativar cartão" icon={<Trash2 className="h-4 w-4" />} onClick={() => inactivateCard(card.id)} title="Excluir" variant="danger" />
                      </div>
                    </td>
                  </tr>
                );
              })}
              {activeCards.length === 0 ? <tr><td className="px-4 py-8 text-center text-stone-500" colSpan={6}>Nenhum cartão cadastrado.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
