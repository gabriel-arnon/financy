"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BarChart3, FileUp, Loader2, Minus, Plus, Sparkles, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { ClassificationRuleDialog } from "@/components/classification-rule-dialog";
import { UiButton } from "@/components/ui-button";
import { getAiFinanceOverview } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { formatAccountName, formatCardWithAccount, getAccountName, getCardNameWithAccount, getCategoryName, isActiveEntity, translateTransactionType } from "@/lib/labels";
import type { Account, AiFinanceOverview, AiSuggestedRule, Card, Category, ClassificationRulePayload, Transaction } from "@/lib/types";

type PeriodKey = "current_month" | "previous_month" | "current_week" | "previous_week" | "last_30" | "last_90" | "custom" | "all";

interface DashboardContentProps {
  transactions: Transaction[];
  categories: Category[];
  accounts: Account[];
  cards: Card[];
}

const incomeTypes = new Set(["income", "refund"]);
const profileNameKey = "financy_profile_name";
const categoryChartColors = ["#ef4444", "#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#14b8a6"];

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

function readStoredProfileName() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(profileNameKey) ?? "";
}

function ruleKey(rule: AiSuggestedRule) {
  return `${rule.keyword}-${rule.category_id}-${rule.transaction_type ?? "all"}`;
}

export function DashboardContent({ transactions, categories, accounts, cards }: DashboardContentProps) {
  const { session } = useAuth();
  const router = useRouter();
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodKey>("current_month");
  const [accountFilter, setAccountFilter] = useState("all");
  const [cardFilter, setCardFilter] = useState("all");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [aiOverview, setAiOverview] = useState<AiFinanceOverview | null>(null);
  const [aiLoading, setAiLoading] = useState(true);
  const [aiError, setAiError] = useState<string | null>(null);
  const [dismissedRuleKeys, setDismissedRuleKeys] = useState<Set<string>>(() => new Set());
  const [ruleInitialValues, setRuleInitialValues] = useState<ClassificationRulePayload | null>(null);
  const [storedProfileName] = useState(() => readStoredProfileName());

  const now = useMemo(() => new Date(), []);
  const metadataName = typeof session?.user.user_metadata?.full_name === "string" ? session.user.user_metadata.full_name : "";
  const displayName = (metadataName || storedProfileName || session?.user.email?.split("@")[0] || "").trim();
  const firstName = displayName.split(/\s+/)[0] || "bem-vindo";
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

  const categoryPieTotal = categorySummary.slice(0, 6).reduce((total, item) => total + item.total, 0);
  const categoryPieItems = categorySummary.slice(0, 6).reduce<Array<{ color: string; end: number; name: string; percentage: number; start: number; total: number }>>((items, item, index) => {
    const percentage = categoryPieTotal > 0 ? (item.total / categoryPieTotal) * 100 : 0;
    const start = items.at(-1)?.end ?? 0;
    return [...items, {
      ...item,
      color: categoryChartColors[index % categoryChartColors.length],
      end: start + percentage,
      percentage,
      start
    }];
  }, []);
  const categoryPieGradient = categoryPieItems.length > 0
    ? `conic-gradient(${categoryPieItems.map((item) => `${item.color} ${item.start}% ${item.end}%`).join(", ")})`
    : "conic-gradient(#e7e5e4 0% 100%)";

  const summaryCards = [
    { label: "Total de entradas", value: formatCurrency(income), icon: TrendingUp, tone: "text-mint", helper: periodLabel },
    { label: "Total de saídas", value: formatCurrency(expenses), icon: TrendingDown, tone: "text-coral", helper: periodLabel },
    { label: "Saldo do período", value: formatCurrency(balance), icon: Wallet, tone: balance >= 0 ? "text-mint" : "text-coral", helper: "Entradas menos saídas" },
    { label: "Transações analisadas", value: String(filteredTransactions.length), icon: BarChart3, tone: "text-ink", helper: "Dentro dos filtros" }
  ];

  const visibleSuggestedRules = (aiOverview?.suggested_rules ?? []).filter((rule) => !dismissedRuleKeys.has(ruleKey(rule)));

  function openSuggestedRule(rule: AiSuggestedRule) {
    setRuleInitialValues({
      keyword: rule.keyword,
      category_id: rule.category_id,
      transaction_type: rule.transaction_type,
      priority: 100,
      status: "active",
      match_scope: "both",
      auto_created: false
    });
  }

  function handleSuggestedRuleCreated() {
    if (ruleInitialValues) {
      setDismissedRuleKeys((current) => new Set(current).add(`${ruleInitialValues.keyword}-${ruleInitialValues.category_id}-${ruleInitialValues.transaction_type ?? "all"}`));
    }
    getAiFinanceOverview()
      .then(setAiOverview)
      .catch((err) => setAiError(err instanceof Error ? err.message : "Falha ao atualizar insights."));
  }

  function viewRenameSuggestions() {
    const ids = aiOverview?.rename_suggestions.map((item) => item.transaction_id).join(",");
    const search = new URLSearchParams();
    search.set("cleanup", "rename");
    if (ids) search.set("transaction_ids", ids);
    router.push(`/transactions?${search.toString()}`);
  }

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-mint">Visão geral</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">
            Olá, {firstName}!
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-stone-500">Aqui está uma visão geral das suas finanças.</p>
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
          <Link href="/transactions?create=income" className="inline-flex h-10 items-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">
            <Plus className="h-4 w-4" />
            Receita
          </Link>
          <Link href="/transactions?create=expense" className="inline-flex h-10 items-center gap-2 rounded-md bg-red-600 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
            <Minus className="h-4 w-4" />
            Despesa
          </Link>
          <Link href="/importacao" className="inline-flex h-10 items-center gap-2 rounded-md bg-mint px-4 text-sm font-medium text-white shadow-sm transition hover:bg-mint/90 focus:outline-none focus:ring-2 focus:ring-mint focus:ring-offset-2">
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
          {categoryPieItems.length > 0 ? (
            <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(12rem,16rem)_1fr] lg:items-center">
              <div
                aria-label="Distribuição de gastos por categoria"
                className="relative mx-auto aspect-square w-full max-w-64 rounded-full shadow-inner"
                role="img"
                style={{ background: categoryPieGradient }}
              >
                <div className="absolute inset-[23%] flex flex-col items-center justify-center rounded-full bg-white text-center shadow-sm">
                  <span className="text-xs font-medium uppercase text-stone-500">Total</span>
                  <span className="mt-1 text-sm font-semibold text-ink">{formatCurrency(categoryPieTotal)}</span>
                </div>
              </div>
              <div className="grid gap-3">
                {categoryPieItems.map((item) => (
                  <div key={item.name} className="flex items-center justify-between gap-3 rounded-md border border-stone-100 px-3 py-2">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="truncate text-sm font-medium text-ink">{item.name}</span>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-ink">{formatCurrency(item.total)}</p>
                      <p className="text-xs text-stone-500">{item.percentage.toFixed(1)}%</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="py-12 text-center text-sm text-stone-500">Sem gastos para gerar gráfico.</p>
          )}
        </div>

        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-ink">Insights</h2>
            <Sparkles className="h-4 w-4 text-mint" />
          </div>
          <div className="mt-4 grid gap-3">
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
              {visibleSuggestedRules.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-stone-500">Regras sugeridas</p>
                  <div className="mt-2 grid gap-2">
                    {visibleSuggestedRules.slice(0, 2).map((rule) => (
                      <div key={`${rule.keyword}-${rule.category_id}`} className="flex flex-col gap-3 rounded-md border border-stone-100 px-3 py-2 text-sm text-stone-700 sm:flex-row sm:items-center sm:justify-between">
                        <span>
                          <span className="font-semibold text-ink">{rule.keyword}</span> para {rule.category_name} ({rule.match_count} ocorrências)
                        </span>
                        <UiButton icon={<Plus className="h-4 w-4" />} onClick={() => openSuggestedRule(rule)} size="sm" variant="secondary">
                          Adicionar regra
                        </UiButton>
                      </div>
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
                        <span className="font-semibold text-ink">{item.description}</span> para {item.suggested_category_name ?? "Sem categoria"}
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
                  <UiButton className="mt-2" onClick={viewRenameSuggestions} size="sm" variant="secondary">
                    Ver transações
                  </UiButton>
                </div>
              ) : null}
            </div>
          ) : null}
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
      <ClassificationRuleDialog
        categories={categories}
        initialValues={ruleInitialValues}
        onClose={() => setRuleInitialValues(null)}
        onCreated={handleSuggestedRuleCreated}
        open={Boolean(ruleInitialValues)}
      />
    </section>
  );
}
