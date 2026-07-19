"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, CreditCard, Landmark, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { NavigatingLink } from "@/components/navigating-link";
import { IconButton, UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createAccount, deleteAccount, getAccounts, getCards, updateAccount } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { accountTypeLabels, formatAccountName, formatCardName, isActiveEntity } from "@/lib/labels";
import type { Account, AccountPayload, AccountType, Card } from "@/lib/types";

const emptyAccount: AccountPayload = {
  name: "",
  institution: "",
  type: "checking",
  balance: "0",
  status: "active"
};

interface AccountsContentProps {
  initialAccounts: Account[];
  initialCards: Card[];
  mode?: "banking" | "investment";
}

export function AccountsContent({ initialAccounts, initialCards, mode = "banking" }: AccountsContentProps) {
  const toast = useToast();
  const [accounts, setAccounts] = useState<Account[]>(initialAccounts);
  const [cards, setCards] = useState<Card[]>(initialCards);
  const initialForm = useMemo<AccountPayload>(() => ({ ...emptyAccount, type: mode === "investment" ? "investment" : "checking" }), [mode]);
  const [accountForm, setAccountForm] = useState<AccountPayload>(initialForm);
  const [editingAccountId, setEditingAccountId] = useState<string | null>(null);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [query, setQuery] = useState("");

  const isInvestmentMode = mode === "investment";
  const activeAccounts = useMemo(() => accounts.filter((account) => isActiveEntity(account) && (isInvestmentMode ? account.type === "investment" : account.type !== "investment")), [accounts, isInvestmentMode]);
  const activeCards = useMemo(() => cards.filter(isActiveEntity), [cards]);
  const filteredAccounts = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return activeAccounts;
    return activeAccounts.filter((account) => {
      const searchable = [account.name, account.institution, accountTypeLabels[account.type]].filter(Boolean).join(" ").toLowerCase();
      return searchable.includes(normalized);
    });
  }, [activeAccounts, query]);
  const accountSummary = useMemo(() => {
    return activeAccounts.reduce(
      (summary, account) => {
        const linkedCards = activeCards.filter((card) => card.account_id === account.id);
        summary.totalBalance += Number(account.balance ?? 0);
        if (linkedCards.length > 0) summary.accountsWithCards += 1;
        return summary;
      },
      { totalBalance: 0, accountsWithCards: 0 }
    );
  }, [activeAccounts, activeCards]);

  async function loadData() {
    const [nextAccounts, nextCards] = await Promise.all([getAccounts(), getCards()]);
    setAccounts(nextAccounts);
    setCards(nextCards);
  }

  useEffect(() => {
    let active = true;
    Promise.all([getAccounts(), getCards()])
      .then(([nextAccounts, nextCards]) => {
        if (!active) return;
        setAccounts(nextAccounts);
        setCards(nextCards);
      })
      .catch((err) => {
        if (active && initialAccounts.length === 0) toast.error(err instanceof Error ? err.message : "Falha ao carregar contas bancárias.");
      });
    return () => {
      active = false;
    };
  }, [initialAccounts.length, toast]);

  async function handleAccountSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = {
        ...accountForm,
        institution: accountForm.institution || null,
        balance: accountForm.balance || "0",
        status: "active" as const
      };
      if (editingAccountId) {
        await updateAccount(editingAccountId, payload);
        toast.success(isInvestmentMode ? "Investimento atualizado." : "Conta atualizada.");
      } else {
        await createAccount(payload);
        toast.success(isInvestmentMode ? "Investimento cadastrado." : "Conta cadastrada.");
      }
      setAccountForm(initialForm);
      setEditingAccountId(null);
      setShowAccountForm(false);
      await loadData();
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Falha ao salvar conta.";
      toast.error(messageText);
    }
  }

  function editAccount(account: Account) {
    setEditingAccountId(account.id);
    setShowAccountForm(true);
    setAccountForm({
      name: account.name,
      institution: account.institution ?? "",
      type: account.type,
      balance: account.balance,
      status: "active"
    });
  }

  async function inactivateAccount(accountId: string) {
    if (!window.confirm("Inativar esta conta? Ela não aparecerá mais nas listagens.")) return;
    try {
      await deleteAccount(accountId);
      toast.danger("Conta inativada.");
      await loadData();
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Falha ao inativar conta.";
      toast.error(messageText);
    }
  }

  function cancelAccountEdit() {
    setEditingAccountId(null);
    setAccountForm(initialForm);
    setShowAccountForm(false);
  }

  function startNewAccount() {
    setEditingAccountId(null);
    setAccountForm(initialForm);
    setShowAccountForm(true);
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-mint">{isInvestmentMode ? "Patrimonio" : "Cadastro"}</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">{isInvestmentMode ? "Investimentos" : "Contas Bancarias"}</h1>
          <p className="mt-2 text-sm text-stone-500">
            {isInvestmentMode ? "Acompanhe contas e posicoes de investimento sincronizadas pelo Open Finance." : "Cadastre e acompanhe contas bancarias. Cartoes vinculados aparecem como entidades relacionadas."}
          </p>
        </div>
        <UiButton icon={<Plus className="h-4 w-4" />} onClick={startNewAccount} variant="primary">
          {isInvestmentMode ? "Novo investimento" : "Nova conta"}
        </UiButton>
      </div>

      <div className={`grid gap-3 sm:grid-cols-2 ${isInvestmentMode ? "xl:grid-cols-2" : "xl:grid-cols-4"}`}>
        <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{isInvestmentMode ? "Total de investimentos" : "Total de contas"}</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{activeAccounts.length}</p>
        </div>
        <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{isInvestmentMode ? "Total investido" : "Saldo total"}</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(accountSummary.totalBalance)}</p>
        </div>
        {!isInvestmentMode ? (
          <>
            <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Contas com cartoes</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{accountSummary.accountsWithCards}</p>
            </div>
            <div className="min-h-[92px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Cartoes vinculados</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{activeCards.filter((card) => card.account_id).length}</p>
            </div>
          </>
        ) : null}
      </div>

      {showAccountForm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/55 px-4 py-6 backdrop-blur-sm">
          <form onSubmit={handleAccountSubmit} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-lg border border-stone-200 bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone-200 px-5 py-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
                <Landmark className="h-5 w-5 text-mint" />
                {editingAccountId ? (isInvestmentMode ? "Editar investimento" : "Editar conta bancaria") : (isInvestmentMode ? "Novo investimento" : "Nova conta bancaria")}
              </h2>
              <button
                aria-label="Fechar formulário"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-ink"
                onClick={cancelAccountEdit}
                type="button"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 px-5 py-5">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Nome</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Nome da conta" value={accountForm.name} onChange={(event) => setAccountForm({ ...accountForm, name: event.target.value })} required />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Instituição</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Banco ou instituição" value={accountForm.institution ?? ""} onChange={(event) => setAccountForm({ ...accountForm, institution: event.target.value })} />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Tipo de conta</span>
                <select className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={accountForm.type} onChange={(event) => setAccountForm({ ...accountForm, type: event.target.value as AccountType })}>
                  {Object.entries(accountTypeLabels)
                    .filter(([value]) => isInvestmentMode ? value === "investment" : value !== "investment")
                    .map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-ink">Saldo inicial</span>
                <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="R$ 0,00" type="number" step="0.01" value={accountForm.balance} onChange={(event) => setAccountForm({ ...accountForm, balance: event.target.value })} />
              </label>
            </div>

            <div className="grid gap-2 border-t border-stone-200 px-5 py-4 sm:grid-cols-2">
              <UiButton onClick={cancelAccountEdit} variant="secondary">
                Cancelar
              </UiButton>
              <UiButton icon={editingAccountId ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
                {editingAccountId ? "Salvar" : "Criar"}
              </UiButton>
            </div>
          </form>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="border-b border-stone-100 px-4 py-3">
          <label className="block max-w-md space-y-1.5">
            <span className="text-sm font-medium text-ink">{isInvestmentMode ? "Filtrar investimentos" : "Filtrar contas"}</span>
            <input
              className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
              placeholder="Busque por nome, instituição ou tipo"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full table-fixed divide-y divide-stone-200 text-sm">
            <colgroup>
              <col className="w-[30%]" />
              <col className="w-[18%]" />
              <col className="w-[17%]" />
              {!isInvestmentMode ? <col className="w-[20%]" /> : null}
              <col className="w-[15%]" />
            </colgroup>
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="px-3 py-3">Conta</th>
                <th className="px-3 py-3">Tipo</th>
                <th className="px-3 py-3">Saldo</th>
                {!isInvestmentMode ? <th className="px-3 py-3">Cartoes vinculados</th> : null}
                <th className="px-3 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filteredAccounts.map((account) => {
                const linkedCards = activeCards.filter((card) => card.account_id === account.id);
                return (
                  <tr key={account.id} className="align-middle">
                    <td className="px-3 py-2.5">
                      <div className="min-w-0">
                        <Link href={`/accounts/${account.id}`} className="inline-flex max-w-full items-center gap-1 font-medium text-ink hover:text-mint">
                          <span className="truncate">{formatAccountName(account)}</span>
                          <ArrowRight className="h-3.5 w-3.5 shrink-0" />
                        </Link>
                        <p className="mt-1 truncate text-xs text-stone-500">{account.institution || "Instituição não informada"}</p>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-stone-600">
                      <p className="font-medium text-stone-700">{accountTypeLabels[account.type]}</p>
                      <p className="mt-1 text-xs text-stone-400">{isInvestmentMode ? "Investimento" : "Conta bancaria"}</p>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-stone-600">{formatCurrency(account.balance)}</td>
                    {!isInvestmentMode ? (
                      <td className="px-3 py-2.5 text-stone-600">
                        {linkedCards.length > 0 ? (
                          <div className="space-y-1">
                            {linkedCards.slice(0, 2).map((card) => (
                              <div key={card.id} className="flex min-w-0 items-center gap-1.5">
                                <CreditCard className="h-3.5 w-3.5 shrink-0 text-stone-400" />
                                <Link href={`/cards/${card.id}`} className="truncate text-sm font-medium text-mint hover:text-emerald-700">
                                  {formatCardName(card)}
                                </Link>
                              </div>
                            ))}
                            {linkedCards.length > 2 ? <p className="text-xs text-stone-400">+{linkedCards.length - 2} cartoes</p> : null}
                          </div>
                        ) : (
                          <span className="text-sm text-stone-400">Nenhum cartao</span>
                        )}
                      </td>
                    ) : null}
                    <td className="px-3 py-2.5">
                      <div className="flex items-center justify-end gap-1.5">
                        <NavigatingLink href={`/accounts/${account.id}`} className="inline-flex h-8 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-stone-300 bg-white px-2.5 text-xs font-medium text-ink shadow-sm hover:bg-stone-50">
                          Detalhes
                          <ArrowRight className="h-3.5 w-3.5 shrink-0" />
                        </NavigatingLink>
                        <IconButton aria-label="Editar conta" icon={<Pencil className="h-4 w-4" />} onClick={() => editAccount(account)} title="Editar" variant="secondary" />
                        <IconButton aria-label="Inativar conta" icon={<Trash2 className="h-4 w-4" />} onClick={() => inactivateAccount(account.id)} title="Excluir" variant="danger" />
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredAccounts.length === 0 ? <tr><td className="px-4 py-8 text-center text-stone-500" colSpan={isInvestmentMode ? 4 : 5}>{activeAccounts.length === 0 ? (isInvestmentMode ? "Nenhum investimento cadastrado." : "Nenhuma conta cadastrada.") : "Nenhum item encontrado para o filtro."}</td></tr> : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
