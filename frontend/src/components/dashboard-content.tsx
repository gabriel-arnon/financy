"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, BarChart3, FileUp, Loader2, Sparkles, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { askAiFinance, getAiFinanceOverview } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { formatAccountName, formatCardWithAccount, getAccountName, getCardNameWithAccount, getCategoryName, isActiveEntity, translateTransactionType } from "@/lib/labels";
import type { Account, AiFinanceOverview, AiFinanceQuestionResponse, Card, Category, Transaction } from "@/lib/types";

type PeriodKey = "current_month" | "previous_month" | "current_week" | "previous_week" | "last_30" | "last_90" | "custom" | "all";

interface DashboardContentProps {
  transactions: Transaction[];
  categories: Category[];
  accounts: Account[];
  cards: Card[];
}

const incomeTypes = new Set(["income", "refund"]);

const periodOptions: Array<{ value: PeriodKey; label: string }> = [
  { value: "current_month", label: "Este mês" },
  { value: "previous_month", label: "Mês passado" },
  { value: "current_week", label: "Esta semana" },
  { value: "previous_week", label: "Semana passada" },
  { value: "last_30", label: "Últimos 30 dias" },
  { value: "last_90", label: "Últimos 90 dias" },
  { value: "custom", label: "Personalizado" },
  { value: "all", label: "Todos" }
];

function monthKey(value: string) {
  return value.slice(0, 7);
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function toDateKey(date: Date) {
  return date.toISOString().slice(0, 10);
}

function weekStart(date: Date) {
  const start = startOfDay(date);
  const day = start.getDay();
  const offset = day === 0 ? -6 : 1 - day;
  start.setDate(start.getDate() + offset);
  return start;
}

function periodRange(period: PeriodKey, today: Date, customStart: string, customEnd: string) {
  if (period === "custom") {
    return {
      start: customStart ? startOfDay(new Date(`${customStart}T00:00:00`)) : null,
      end: customEnd ? startOfDay(new Date(`${customEnd}T00:00:00`)) : null
    };
  }
  if (period === "current_month" || period === "previous_month") {
    const offset = period === "previous_month" ? -1 : 0;
    return {
      start: new Date(today.getFullYear(), today.getMonth() + offset, 1),
      end: new Date(today.getFullYear(), today.getMonth() + offset + 1, 0)
    };
  }
  if (period === "current_week" || period === "previous_week") {
    const start = weekStart(today);
    if (period === "previous_week") start.setDate(start.getDate() - 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return { start, end };
  }
  if (period === "last_30" || period === "last_90") {
    const days = period === "last_30" ? 30 : 90;
    const start = new Date(today);
    start.setDate(today.getDate() - days + 1);
    return { start, end: today };
  }
  return { start: null, end: null };
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
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [aiOverview, setAiOverview] = useState<AiFinanceOverview | null>(null);
  const [aiLoading, setAiLoading] = useState(true);
  const [aiQuestion, setAiQuestion] = useState("");
  const [aiAnswer, setAiAnswer] = useState<AiFinanceQuestionResponse | null>(null);
  const [aiAnswerLoading, setAiAnswerLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const now = useMemo(() => new Date(), []);
  const currentMonth = now.toISOString().slice(0, 7);
  const hasCurrentMonthTransactions = transactions.some((transaction) => monthKey(transaction.transaction_date) === currentMonth);
  const fallbackApplied = selectedPeriod === "current_month" && !hasCurrentMonthTransactions && transactions.length > 0;
  const effectivePeriod: PeriodKey = fallbackApplied ? "all" : selectedPeriod;
  const cardAccountById = useMemo(() => new Map(cards.map((card) => [card.id, card.account_id])), [cards]);

  useEffect(() => {
    let active = true;
    getAiFinanceOverview()
      .then((overview) => {
        if (!active) return;
        setAiOverview(overview);
        setAiError(null);
      })
      .catch((err) => {
        if (!active) return;
        setAiError(err instanceof Error ? err.message : "Falha ao carregar inteligência financeira.");
      })
      .finally(() => {
        if (active) setAiLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleAiQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = aiQuestion.trim();
    if (question.length < 3) return;
    setAiAnswerLoading(true);
    setAiError(null);
    try {
      const answer = await askAiFinance(question);
      setAiAnswer(answer);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Falha ao responder pergunta financeira.");
    } finally {
      setAiAnswerLoading(false);
    }
  }

  const filteredTransactions = useMemo(() => {
    const today = startOfDay(now);
    const { start, end } = periodRange(effectivePeriod, today, customStartDate, customEndDate);
    return transactions.filter((transaction) => {
      const matchesAccount =
        accountFilter === "all" ||
        transaction.account_id === accountFilter ||
        (transaction.card_id ? cardAccountById.get(transaction.card_id) === accountFilter : false);
      const matchesCard = cardFilter === "all" || transaction.card_id === cardFilter;
      const transactionDate = startOfDay(new Date(`${transaction.transaction_date}T00:00:00`));
      return matchesAccount && matchesCard && (!start || transactionDate >= start) && (!end || transactionDate <= end);
    });
  }, [accountFilter, cardAccountById, cardFilter, customEndDate, customStartDate, effectivePeriod, now, transactions]);

  const income = filteredTransactions
    .filter((transaction) => incomeTypes.has(transaction.type))
    .reduce((total, transaction) => total + Number(transaction.amount), 0);
  const expenses = filteredTransactions
    .filter((transaction) => transaction.type === "expense")
    .reduce((total, transaction) => total + Number(transaction.amount), 0);
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
  const maxCategoryTotal = Math.max(...categorySummary.map((item) => item.total), 1);
  const dailySummary = Object.entries(
    filteredTransactions.reduce<Record<string, { income: number; expenses: number }>>((summary, transaction) => {
      const key = transaction.transaction_date.slice(5, 10);
      const current = summary[key] ?? { income: 0, expenses: 0 };
      if (incomeTypes.has(transaction.type)) current.income += Math.abs(Number(transaction.amount));
      if (transaction.type === "expense") current.expenses += Math.abs(Number(transaction.amount));
      summary[key] = current;
      return summary;
    }, {})
  ).slice(-8);
  const maxDailyTotal = Math.max(...dailySummary.map(([, item]) => Math.max(item.income, item.expenses)), 1);
  const biggestExpense = filteredTransactions
    .filter((transaction) => transaction.type === "expense")
    .sort((a, b) => Number(b.amount) - Number(a.amount))[0];
  const topCategory = categorySummary[0];
  const insights = [
    topCategory ? `Maior categoria de gastos: ${topCategory.name}, com ${formatCurrency(topCategory.total)}.` : "Nenhum gasto encontrado no período filtrado.",
    biggestExpense ? `Maior despesa: ${biggestExpense.description}, no valor de ${formatCurrency(biggestExpense.amount)}.` : "Nenhuma despesa confirmada no período.",
    balance >= 0 ? `Resultado positivo de ${formatCurrency(balance)} no período.` : `Resultado negativo de ${formatCurrency(Math.abs(balance))} no período.`
  ];

  const summaryCards = [
    { label: "Total de entradas", value: formatCurrency(income), icon: TrendingUp, tone: "text-mint", helper: periodLabel },
    { label: "Total de saídas", value: formatCurrency(expenses), icon: TrendingDown, tone: "text-coral", helper: periodLabel },
    { label: "Saldo do período", value: formatCurrency(balance), icon: Wallet, tone: balance >= 0 ? "text-mint" : "text-coral", helper: "Entradas menos saídas" },
    { label: "Transações analisadas", value: String(filteredTransactions.length), icon: BarChart3, tone: "text-ink", helper: "Dentro dos filtros" }
  ];

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-mint">Visão geral</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Dashboard financeiro</h1>
          <p className="mt-2 max-w-2xl text-sm text-stone-500">Acompanhe o resumo do período, gráficos de gastos e insights rápidos.</p>
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
          {selectedPeriod === "custom" ? (
            <>
              <input className="h-10 rounded-md border border-stone-200 bg-white px-3 text-sm outline-none focus:border-mint" type="date" value={customStartDate} onChange={(event) => setCustomStartDate(event.target.value)} max={customEndDate || undefined} />
              <input className="h-10 rounded-md border border-stone-200 bg-white px-3 text-sm outline-none focus:border-mint" type="date" value={customEndDate} onChange={(event) => setCustomEndDate(event.target.value)} min={customStartDate || undefined} max={toDateKey(now)} />
            </>
          ) : null}
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

      <div className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-ink">Gastos por categoria</h2>
          <div className="mt-5 grid gap-4">
            {categorySummary.slice(0, 6).map((item) => (
              <div key={item.name}>
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span className="font-medium text-ink">{item.name}</span>
                  <span className="font-semibold text-ink">{formatCurrency(item.total)}</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-100">
                  <div className="h-full rounded-full bg-coral" style={{ width: `${Math.max((item.total / maxCategoryTotal) * 100, 4)}%` }} />
                </div>
              </div>
            ))}
            {categorySummary.length === 0 ? <p className="py-6 text-center text-sm text-stone-500">Sem gastos para gerar gráfico.</p> : null}
          </div>
        </div>

        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-ink">Insights</h2>
            <Sparkles className="h-4 w-4 text-mint" />
          </div>
          <div className="mt-4 grid gap-3">
            {insights.map((insight) => (
              <p key={insight} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-700">{insight}</p>
            ))}
            {aiOverview?.insights.slice(0, 2).map((insight) => (
              <p key={`${insight.title}-${insight.description}`} className="rounded-md bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-900">
                <span className="font-semibold">{insight.title}: </span>{insight.description}
              </p>
            ))}
            {aiLoading ? (
              <p className="inline-flex items-center gap-2 rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Gerando sugestões...
              </p>
            ) : null}
            {aiError ? <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{aiError}</p> : null}
          </div>
          {aiOverview ? (
            <div className="mt-4 grid gap-3 border-t border-stone-100 pt-4">
              <p className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-700">{aiOverview.summary}</p>
              {aiOverview.suggested_rules.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-stone-500">Regras sugeridas</p>
                  <div className="mt-2 grid gap-2">
                    {aiOverview.suggested_rules.slice(0, 2).map((rule) => (
                      <p key={`${rule.keyword}-${rule.category_id}`} className="rounded-md border border-stone-100 px-3 py-2 text-sm text-stone-700">
                        <span className="font-semibold text-ink">{rule.keyword}</span> → {rule.category_name} ({rule.match_count} ocorrências)
                      </p>
                    ))}
                  </div>
                </div>
              ) : null}
              {aiOverview.category_suggestions.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-stone-500">Classificação automática</p>
                  <div className="mt-2 grid gap-2">
                    {aiOverview.category_suggestions.slice(0, 2).map((item) => (
                      <p key={item.transaction_id} className="rounded-md border border-stone-100 px-3 py-2 text-sm text-stone-700">
                        <span className="font-semibold text-ink">{item.description}</span> → {item.suggested_category_name ?? "Sem categoria"}
                      </p>
                    ))}
                  </div>
                </div>
              ) : null}
              {aiOverview.recurrence_suggestions.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-stone-500">Recorrências prováveis</p>
                  <div className="mt-2 grid gap-2">
                    {aiOverview.recurrence_suggestions.slice(0, 2).map((item) => (
                      <p key={`${item.description}-${item.amount}`} className="rounded-md border border-stone-100 px-3 py-2 text-sm text-stone-700">
                        <span className="font-semibold text-ink">{item.description}</span> · {formatCurrency(item.amount)} · {item.cadence}
                      </p>
                    ))}
                  </div>
                </div>
              ) : null}
              {aiOverview.rename_suggestions.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-stone-500">Descrições para limpar</p>
                  <p className="mt-2 rounded-md border border-stone-100 px-3 py-2 text-sm text-stone-700">
                    {aiOverview.rename_suggestions.length} descrições têm sugestão de renomeação automática.
                  </p>
                </div>
              ) : null}
            </div>
          ) : null}
          <form className="mt-4 grid gap-2 border-t border-stone-100 pt-4" onSubmit={handleAiQuestion}>
            <label className="text-sm font-medium text-ink" htmlFor="ai-finance-question">Pergunte sobre suas finanças</label>
            <div className="flex gap-2">
              <input
                id="ai-finance-question"
                className="h-10 min-w-0 flex-1 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
                placeholder="Ex: quanto gastei em mercado?"
                value={aiQuestion}
                onChange={(event) => setAiQuestion(event.target.value)}
              />
              <UiButton disabled={aiAnswerLoading} icon={aiAnswerLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} type="submit" variant="secondary">
                Perguntar
              </UiButton>
            </div>
            {aiAnswer ? <p className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-700">{aiAnswer.answer}</p> : null}
          </form>
          <div className="mt-5 flex h-28 items-end gap-2 border-t border-stone-100 pt-4">
            {dailySummary.map(([key, item]) => (
              <div key={key} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                <div className="flex h-20 w-full items-end gap-1">
                  <div className="w-full rounded-t bg-coral" style={{ height: `${Math.max((item.expenses / maxDailyTotal) * 100, 4)}%` }} title={`Saídas ${formatCurrency(item.expenses)}`} />
                  <div className="w-full rounded-t bg-mint" style={{ height: `${Math.max((item.income / maxDailyTotal) * 100, 4)}%` }} title={`Entradas ${formatCurrency(item.income)}`} />
                </div>
                <span className="truncate text-[10px] text-stone-500">{key}</span>
              </div>
            ))}
          </div>
        </div>
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
