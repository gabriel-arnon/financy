"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, CircleAlert, FileUp, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { formatCurrency, formatDate } from "@/lib/format";
import { formatAccountName, formatCardWithAccount, getAccountName, getCardNameWithAccount, getCategoryName, isActiveEntity, translateTransactionType } from "@/lib/labels";
import type { Account, Card, Category, Transaction } from "@/lib/types";

type PeriodKey = "current_month" | "last_30" | "last_90" | "all";

interface DashboardContentProps {
  transactions: Transaction[];
  categories: Category[];
  accounts: Account[];
  cards: Card[];
}

const periodOptions: Array<{ value: PeriodKey; label: string }> = [
  { value: "current_month", label: "Mês atual" },
  { value: "last_30", label: "Últimos 30 dias" },
  { value: "last_90", label: "Últimos 90 dias" },
  { value: "all", label: "Todos" }
];

function monthKey(value: string) {
  return value.slice(0, 7);
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function sortByDateDesc(a: Transaction, b: Transaction) {
  const dateCompare = b.transaction_date.localeCompare(a.transaction_date);
  if (dateCompare !== 0) return dateCompare;
  return (b.created_at ?? "").localeCompare(a.created_at ?? "");
}

export function DashboardContent({ transactions, categories, accounts, cards }: DashboardContentProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodKey>("current_month");
  const [accountFilter, setAccountFilter] = useState("all");
  const [cardFilter, setCardFilter] = useState("all");

  const now = useMemo(() => new Date(), []);
  const currentMonth = now.toISOString().slice(0, 7);
  const hasCurrentMonthTransactions = transactions.some((transaction) => monthKey(transaction.transaction_date) === currentMonth);
  const fallbackApplied = selectedPeriod === "current_month" && !hasCurrentMonthTransactions && transactions.length > 0;
  const effectivePeriod: PeriodKey = fallbackApplied ? "all" : selectedPeriod;
  const cardAccountById = useMemo(() => new Map(cards.map((card) => [card.id, card.account_id])), [cards]);

  const filteredTransactions = useMemo(() => {
    const today = startOfDay(now);
    return transactions.filter((transaction) => {
      const matchesAccount =
        accountFilter === "all" ||
        transaction.account_id === accountFilter ||
        (transaction.card_id ? cardAccountById.get(transaction.card_id) === accountFilter : false);
      const matchesCard = cardFilter === "all" || transaction.card_id === cardFilter;
      if (effectivePeriod === "all") return matchesAccount && matchesCard;
      if (effectivePeriod === "current_month") {
        return monthKey(transaction.transaction_date) === currentMonth && matchesAccount && matchesCard;
      }

      const days = effectivePeriod === "last_30" ? 30 : 90;
      const start = new Date(today);
      start.setDate(today.getDate() - days + 1);
      const transactionDate = startOfDay(new Date(`${transaction.transaction_date}T00:00:00`));
      return transactionDate >= start && transactionDate <= today && matchesAccount && matchesCard;
    });
  }, [accountFilter, cardAccountById, cardFilter, currentMonth, effectivePeriod, now, transactions]);

  const income = filteredTransactions
    .filter((transaction) => transaction.type === "income" || transaction.type === "refund")
    .reduce((total, transaction) => total + Number(transaction.amount), 0);
  const expenses = filteredTransactions
    .filter((transaction) => transaction.type === "expense")
    .reduce((total, transaction) => total + Number(transaction.amount), 0);
  const pending = filteredTransactions.filter((transaction) => transaction.status === "pending").length;
  const balance = income - expenses;
  const periodLabel = periodOptions.find((option) => option.value === effectivePeriod)?.label ?? "Período";

  const latestTransactions = [...filteredTransactions].sort(sortByDateDesc).slice(0, 5);
  const categorySummary = Object.entries(
    filteredTransactions
      .filter((transaction) => transaction.type === "expense")
      .reduce<Record<string, number>>((summary, transaction) => {
        const name = getCategoryName(transaction.category_id, categories);
        summary[name] = (summary[name] ?? 0) + Number(transaction.amount);
        return summary;
      }, {})
  )
    .map(([name, total]) => ({ name, total }))
    .sort((a, b) => b.total - a.total);

  const summaryCards = [
    { label: "Total de entradas", value: formatCurrency(income), icon: TrendingUp, tone: "text-mint", helper: periodLabel },
    { label: "Total de saídas", value: formatCurrency(expenses), icon: TrendingDown, tone: "text-coral", helper: periodLabel },
    { label: "Saldo do período", value: formatCurrency(balance), icon: Wallet, tone: balance >= 0 ? "text-mint" : "text-coral", helper: "Entradas menos saídas" },
    { label: "Pendentes de revisão", value: String(pending), icon: CircleAlert, tone: "text-amber-600", helper: "Transações com status pending" }
  ];

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-mint">Visão geral</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Dashboard financeiro</h1>
          <p className="mt-2 max-w-2xl text-sm text-stone-500">Acompanhe o resumo do período e avance rapidamente para importações ou revisão de lançamentos.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {accounts.some(isActiveEntity) ? (
            <select className="h-10 rounded-md border border-stone-200 bg-white px-3 text-sm outline-none focus:border-mint" value={accountFilter} onChange={(event) => setAccountFilter(event.target.value)}>
              <option value="all">Todas as contas</option>
              {accounts.filter(isActiveEntity).map((account) => <option key={account.id} value={account.id}>{formatAccountName(account)}</option>)}
            </select>
          ) : null}
          {cards.some(isActiveEntity) ? (
            <select className="h-10 rounded-md border border-stone-200 bg-white px-3 text-sm outline-none focus:border-mint" value={cardFilter} onChange={(event) => setCardFilter(event.target.value)}>
              <option value="all">Todos os cartões</option>
              {cards.filter(isActiveEntity).map((card) => <option key={card.id} value={card.id}>{formatCardWithAccount(card, accounts)}</option>)}
            </select>
          ) : null}
          <select
            className="h-10 rounded-md border border-stone-200 bg-white px-3 text-sm outline-none focus:border-mint"
            value={selectedPeriod}
            onChange={(event) => setSelectedPeriod(event.target.value as PeriodKey)}
          >
            {periodOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <Link href="/importacao" className="inline-flex items-center gap-2 rounded-md bg-mint px-4 py-2 text-sm font-medium text-white shadow-sm">
            <FileUp className="h-4 w-4" />
            Importar arquivo
          </Link>
        </div>
      </div>

      {fallbackApplied ? (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Sem transações no mês atual. Exibindo todos os lançamentos.
        </p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-stone-500">{card.label}</p>
                  <p className="mt-2 text-2xl font-semibold text-ink">{card.value}</p>
                </div>
                <Icon className={`h-5 w-5 ${card.tone}`} />
              </div>
              <p className="mt-4 text-xs text-stone-500">{card.helper}</p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Últimas transações</h2>
            <Link href="/transactions" className="inline-flex items-center gap-1 text-sm font-medium text-mint">
              Ver todas
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="divide-y divide-stone-100">
            {latestTransactions.map((transaction) => (
              <div key={transaction.id} className="grid gap-2 px-5 py-4 sm:grid-cols-[1fr_auto]">
                <div>
                  <p className="font-medium text-ink">{transaction.description}</p>
                  <p className="mt-1 text-xs text-stone-500">
                    {formatDate(transaction.transaction_date)} · {translateTransactionType(transaction.type)} · {getCategoryName(transaction.category_id, categories)}
                    {transaction.card_id ? ` · Cartão: ${getCardNameWithAccount(transaction.card_id, cards, accounts)}` : ""}
                    {transaction.account_id ? ` · Conta: ${getAccountName(transaction.account_id, accounts)}` : ""}
                  </p>
                </div>
                <p className="text-right font-semibold text-ink">{formatCurrency(transaction.amount)}</p>
              </div>
            ))}
            {latestTransactions.length === 0 ? (
              <p className="px-5 py-12 text-center text-sm text-stone-500">Nenhuma transação no período.</p>
            ) : null}
          </div>
        </div>

        <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Resumo por categoria</h2>
            <p className="mt-1 text-xs text-stone-500">Gastos ordenados do maior para o menor.</p>
          </div>
          <div className="divide-y divide-stone-100">
            {categorySummary.map((item) => (
              <div key={item.name} className="flex items-center justify-between gap-4 px-5 py-4">
                <span className="text-sm font-medium text-ink">{item.name}</span>
                <span className="text-sm font-semibold text-ink">{formatCurrency(item.total)}</span>
              </div>
            ))}
            {categorySummary.length === 0 ? (
              <p className="px-5 py-12 text-center text-sm text-stone-500">Nenhum gasto no período.</p>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
