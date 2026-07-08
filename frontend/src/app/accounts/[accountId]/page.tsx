import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight, CreditCard, Landmark, ReceiptText, Wallet } from "lucide-react";
import { NavigatingLink } from "@/components/navigating-link";
import { StatementDeleteButton } from "@/components/statement-delete-button";
import { serverGetAccountSummary, serverGetCategories } from "@/lib/server-api";
import { formatCurrency, formatDate } from "@/lib/format";
import {
  accountTypeLabels,
  formatAccountName,
  formatCardName,
  getCategoryName,
  translateStatementStatus,
  translateTransactionType
} from "@/lib/labels";
import type { AccountSummary, CardStatementSummary } from "@/lib/types";

interface AccountDetailPageProps {
  params: Promise<{ accountId: string }>;
  searchParams?: Promise<{ start_date?: string; end_date?: string }>;
}

type PeriodKey = "all" | "current_month" | "previous_month" | "last_90";

export const dynamic = "force-dynamic";

function toDateKey(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function monthRange(offset: number) {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() + offset, 1);
  const end = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0);
  return { start_date: toDateKey(start), end_date: toDateKey(end) };
}

function last90Range() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - 89);
  return { start_date: toDateKey(start), end_date: toDateKey(end) };
}

const periodOptions: Array<{ key: PeriodKey; label: string; range: { start_date?: string; end_date?: string } }> = [
  { key: "all", label: "Todos", range: {} },
  { key: "current_month", label: "Mês atual", range: monthRange(0) },
  { key: "previous_month", label: "Mês passado", range: monthRange(-1) },
  { key: "last_90", label: "Últimos 90 dias", range: last90Range() }
];

function periodHref(accountId: string, range: { start_date?: string; end_date?: string }) {
  const search = new URLSearchParams();
  if (range.start_date) search.set("start_date", range.start_date);
  if (range.end_date) search.set("end_date", range.end_date);
  const query = search.toString();
  return `/accounts/${accountId}${query ? `?${query}` : ""}`;
}

function activePeriod(startDate?: string, endDate?: string): PeriodKey {
  const found = periodOptions.find((option) => option.range.start_date === startDate && option.range.end_date === endDate);
  return found?.key ?? "all";
}

function integrityClass(status: CardStatementSummary["integrity_status"]) {
  if (status === "difference") return "bg-red-50 text-red-700";
  if (status === "no_transactions") return "bg-amber-50 text-amber-800";
  return "bg-emerald-50 text-emerald-700";
}

function statementRowClass(status: CardStatementSummary["integrity_status"]) {
  if (status === "no_transactions") return "bg-amber-50/60 hover:bg-amber-50";
  if (status === "difference") return "bg-red-50/40 hover:bg-red-50";
  return "hover:bg-stone-50";
}

function statementTotal(statement: CardStatementSummary): string {
  return statement.reported_total ?? statement.calculated_total;
}

export default async function AccountDetailPage({ params, searchParams }: AccountDetailPageProps) {
  const { accountId } = await params;
  const resolvedSearchParams = await searchParams;
  const startDate = resolvedSearchParams?.start_date;
  const endDate = resolvedSearchParams?.end_date;
  const [summary, categories] = await Promise.all([
    serverGetAccountSummary(accountId, { start_date: startDate, end_date: endDate }).catch(() => null),
    serverGetCategories().catch(() => [])
  ]);

  if (!summary) {
    notFound();
  }

  const typedSummary = summary as AccountSummary;
  const currentPeriod = activePeriod(startDate, endDate);
  const bankDetails = [
    { label: "Instituição", value: typedSummary.account.institution ?? "Não informada" },
    { label: "Agência", value: typedSummary.account.agency ?? "Não informada" },
    { label: "Conta", value: typedSummary.account.account_number ?? "Não informada" },
    { label: "Tipo", value: accountTypeLabels[typedSummary.account.type] }
  ];
  const summaryCards = [
    { label: "Saldo informado", value: formatCurrency(typedSummary.account.balance), helper: "Cadastro da conta", icon: Landmark },
    { label: "Entradas no período", value: formatCurrency(typedSummary.total_income), helper: "Receitas e estornos", icon: ArrowRight },
    { label: "Saídas no período", value: formatCurrency(typedSummary.total_expense), helper: "Despesas confirmadas", icon: Wallet },
    { label: "Resultado do período", value: formatCurrency(typedSummary.net_balance_period), helper: "Entradas menos saídas", icon: Wallet }
  ];

  return (
    <section className="space-y-6">
      <div>
        <Link href="/accounts" className="inline-flex items-center gap-2 text-sm font-medium text-mint">
          <ArrowLeft className="h-4 w-4" />
          Voltar para contas
        </Link>
        <p className="mt-4 text-sm font-medium text-mint">Detalhe operacional</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">{formatAccountName(typedSummary.account)}</h1>
        <p className="mt-2 text-sm text-stone-500">
          {typedSummary.account.institution ?? "Instituição não informada"} · {accountTypeLabels[typedSummary.account.type]} · {typedSummary.transaction_count} transações no período
        </p>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-ink">Dados bancários</h2>
        <p className="mt-1 text-sm text-stone-500">Informações identificadas na conta ou no extrato importado.</p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {bankDetails.map((detail) => (
            <div key={detail.label} className="rounded-md border border-stone-100 bg-stone-50 px-4 py-3">
              <dt className="text-xs font-medium uppercase text-stone-500">{detail.label}</dt>
              <dd className="mt-1 break-words text-sm font-semibold text-ink">{detail.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="flex flex-wrap gap-2">
        {periodOptions.map((option) => {
          const isActive = option.key === currentPeriod;
          return (
            <Link
              key={option.key}
              href={periodHref(accountId, option.range)}
              className={`inline-flex min-h-9 items-center justify-center whitespace-nowrap rounded-md border px-3 py-2 text-sm font-medium ${
                isActive ? "border-mint bg-mint text-white" : "border-stone-200 bg-white text-stone-700 hover:bg-stone-50"
              }`}
            >
              {option.label}
            </Link>
          );
        })}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-stone-500">{card.label}</p>
                  <p className="mt-2 text-xl font-semibold text-ink">{card.value}</p>
                </div>
                <Icon className="h-5 w-5 text-mint" />
              </div>
              <p className="mt-4 text-xs text-stone-500">{card.helper}</p>
            </div>
          );
        })}
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-stone-500">Faturas abertas</p>
              <p className="mt-2 text-xl font-semibold text-ink">{formatCurrency(typedSummary.total_open_statements_ok)}</p>
            </div>
            <ReceiptText className="h-5 w-5 text-mint" />
          </div>
          <div className="mt-4 grid gap-2 text-xs">
            <div className="flex items-center justify-between gap-3">
              <span className="text-stone-500">Total válido</span>
              <span className="font-semibold text-ink">{formatCurrency(typedSummary.total_open_statements_ok)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-amber-700">Em alerta</span>
              <span className="font-semibold text-amber-700">{formatCurrency(typedSummary.total_open_statements_warning)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Cartões vinculados</h2>
            <p className="mt-1 text-xs text-stone-500">Cartões ativos desta conta.</p>
          </div>
          <div className="grid gap-3 p-5">
            {typedSummary.cards.map((card) => (
              <article key={card.id} className="rounded-lg border border-stone-100 bg-stone-50 p-4">
                <div className="flex items-start gap-3">
                  <CreditCard className="mt-0.5 h-5 w-5 shrink-0 text-mint" />
                  <div className="min-w-0">
                    <p className="break-words font-semibold text-ink">{formatCardName(card)}</p>
                    <p className="mt-1 text-sm text-stone-500">Limite {card.limit_amount ? formatCurrency(card.limit_amount) : "-"}</p>
                    <p className="mt-2 text-xs text-stone-500">
                      {card.open_statement_count} faturas abertas · {formatCurrency(card.open_statement_total)}
                    </p>
                    <NavigatingLink href={`/cards/${card.id}`} className="mt-3 inline-flex min-h-9 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-mint">
                      Ver cartão
                      <ArrowRight className="h-4 w-4" />
                    </NavigatingLink>
                  </div>
                </div>
              </article>
            ))}
            {typedSummary.cards.length === 0 ? (
              <p className="rounded-lg border border-stone-100 bg-stone-50 px-4 py-8 text-center text-sm text-stone-500">Nenhum cartão vinculado.</p>
            ) : null}
          </div>
        </div>

        <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Faturas abertas</h2>
            <p className="mt-1 text-xs text-stone-500">Faturas abertas ou vencidas dos cartões da conta.</p>
          </div>
          <div className="divide-y divide-stone-100">
            {typedSummary.open_statements.map((statement) => {
              const card = typedSummary.cards.find((item) => item.id === statement.card_id);
              return (
                <article key={statement.id} className={`grid gap-3 px-5 py-4 sm:grid-cols-[1fr_auto] ${statementRowClass(statement.integrity_status)}`}>
                  <div className="min-w-0">
                    <p className="break-words font-medium text-ink">{card ? formatCardName(card) : "Cartão não encontrado"}</p>
                    <p className="mt-1 text-xs text-stone-500">
                      Referência {formatDate(statement.reference_month)} · Vencimento {statement.due_date ? formatDate(statement.due_date) : "-"} · {translateStatementStatus(statement.status)}
                    </p>
                    <span className={`mt-2 inline-flex rounded-md px-2 py-1 text-xs font-medium ${integrityClass(statement.integrity_status)}`}>
                      {statement.integrity_label}
                    </span>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="font-semibold text-ink">{formatCurrency(statementTotal(statement))}</p>
                    <p className="mt-1 text-xs text-stone-500">{statement.transaction_count} transações</p>
                    <div className="mt-3 grid gap-2 sm:justify-end">
                      {statement.integrity_status === "no_transactions" ? (
                        <StatementDeleteButton compact statementId={statement.id} />
                      ) : null}
                      <Link href={`/statements/${statement.id}`} className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-2.5 py-2 text-sm font-medium text-mint">
                        Detalhes
                        <ArrowRight className="h-4 w-4 shrink-0" />
                      </Link>
                    </div>
                  </div>
                </article>
              );
            })}
            {typedSummary.open_statements.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-stone-500">Nenhuma fatura aberta.</p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="border-b border-stone-100 px-5 py-4">
          <h2 className="text-base font-semibold text-ink">Últimas transações relacionadas</h2>
          <p className="mt-1 text-xs text-stone-500">Transações diretas da conta e dos cartões vinculados.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-[760px] divide-y divide-stone-200 text-sm">
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3">Descrição</th>
                <th className="px-4 py-3">Origem</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3 text-right">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {typedSummary.recent_transactions.map((transaction) => {
                const card = typedSummary.cards.find((item) => item.id === transaction.card_id);
                return (
                  <tr key={transaction.id}>
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">{formatDate(transaction.transaction_date)}</td>
                    <td className="px-4 py-3 font-medium text-ink">{transaction.description}</td>
                    <td className="px-4 py-3 text-stone-600">{card ? `Cartão: ${formatCardName(card)}` : "Conta"}</td>
                    <td className="px-4 py-3 text-stone-600">{translateTransactionType(transaction.type)}</td>
                    <td className="px-4 py-3 text-stone-600">{getCategoryName(transaction.category_id, categories)}</td>
                    <td className="px-4 py-3 text-right font-medium text-ink">{formatCurrency(transaction.amount)}</td>
                  </tr>
                );
              })}
              {typedSummary.recent_transactions.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-stone-500" colSpan={6}>Nenhuma transação relacionada.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
