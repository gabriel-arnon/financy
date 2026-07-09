import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight, CreditCard, Landmark, ReceiptText, WalletCards } from "lucide-react";
import { NavigatingLink } from "@/components/navigating-link";
import { serverGetCardSummary, serverGetCategories } from "@/lib/server-api";
import { formatCurrency, formatDate } from "@/lib/format";
import {
  accountTypeLabels,
  formatAccountName,
  formatCardName,
  getCategoryName,
  translateStatementStatus,
  translateTransactionType
} from "@/lib/labels";
import type { CardSummaryStatement } from "@/lib/types";

interface CardDetailPageProps {
  params: Promise<{ cardId: string }>;
}

export const dynamic = "force-dynamic";

function integrityClass(status: CardSummaryStatement["integrity_status"]) {
  if (status === "difference") return "bg-red-50 text-red-700";
  if (status === "no_transactions") return "bg-amber-50 text-amber-800";
  return "bg-emerald-50 text-emerald-700";
}

function usageTone(percent: number | null) {
  if (percent === null) return { bar: "bg-stone-300", text: "text-stone-500" };
  if (percent >= 95) return { bar: "bg-red-600", text: "text-red-700" };
  if (percent >= 80) return { bar: "bg-coral", text: "text-coral" };
  if (percent >= 50) return { bar: "bg-amber-500", text: "text-amber-700" };
  return { bar: "bg-mint", text: "text-mint" };
}

function statementAmount(statement: CardSummaryStatement): string {
  return statement.reported_total ?? statement.calculated_total;
}

export default async function CardDetailPage({ params }: CardDetailPageProps) {
  const { cardId } = await params;
  const [summary, categories] = await Promise.all([
    serverGetCardSummary(cardId).catch(() => null),
    serverGetCategories().catch(() => [])
  ]);

  if (!summary) {
    notFound();
  }

  const usage = summary.usage_percent === null ? null : Number(summary.usage_percent);
  const tone = usageTone(usage);
  const usageWidth = usage === null ? 0 : Math.min(Math.max(usage, 0), 100);
  const linkedAccount = summary.account;
  const summaryCards = [
    { label: "Limite total", value: summary.limit_total ? formatCurrency(summary.limit_total) : "Indisponivel", helper: summary.limit_total ? "Limite cadastrado" : "Nenhum limite informado.", icon: CreditCard },
    { label: "Utilizado", value: formatCurrency(summary.limit_used), helper: "Soma das faturas abertas e vencidas", icon: ReceiptText },
    { label: "Disponivel", value: summary.limit_available ? formatCurrency(summary.limit_available) : "Indisponivel", helper: summary.limit_total ? "Limite menos utilizado" : "Nenhum limite informado.", icon: WalletCards }
  ];

  return (
    <section className="space-y-6">
      <div>
        <Link href="/cards" className="inline-flex items-center gap-2 text-sm font-medium text-mint">
          <ArrowLeft className="h-4 w-4" />
          Voltar para cartoes
        </Link>
        <p className="mt-4 text-sm font-medium text-mint">Detalhe operacional</p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-ink">{formatCardName(summary.card)}</h1>
            <p className="mt-2 text-sm text-stone-500">
              Final {summary.card.last_digits} - {linkedAccount ? formatAccountName(linkedAccount) : "Sem conta vinculada"}
            </p>
          </div>
          {linkedAccount ? (
            <NavigatingLink href={`/accounts/${linkedAccount.id}`} className="inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded-md border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-mint shadow-sm">
              Ver conta
              <ArrowRight className="h-4 w-4" />
            </NavigatingLink>
          ) : null}
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Uso do limite</h2>
            <p className={`mt-1 text-sm font-medium ${tone.text}`}>{usage === null ? "Nenhum limite informado." : `${usage.toFixed(2)}% utilizado`}</p>
          </div>
          <p className="text-sm text-stone-500">{formatCurrency(summary.limit_used)} em faturas abertas/vencidas</p>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-stone-100">
          <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${usageWidth}%` }} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <Landmark className="mt-0.5 h-5 w-5 shrink-0 text-mint" />
            <div className="min-w-0 flex-1">
              <h2 className="text-base font-semibold text-ink">Conta vinculada</h2>
              {linkedAccount ? (
                <>
                  <p className="mt-3 break-words text-lg font-semibold text-ink">{formatAccountName(linkedAccount)}</p>
                  <dl className="mt-4 grid gap-3 text-sm">
                    <div className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2">
                      <dt className="text-xs font-medium uppercase text-stone-500">Instituicao</dt>
                      <dd className="mt-1 font-medium text-ink">{linkedAccount.institution ?? "Nao informada"}</dd>
                    </div>
                    <div className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2">
                      <dt className="text-xs font-medium uppercase text-stone-500">Tipo</dt>
                      <dd className="mt-1 font-medium text-ink">{accountTypeLabels[linkedAccount.type]}</dd>
                    </div>
                    <div className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2">
                      <dt className="text-xs font-medium uppercase text-stone-500">Saldo</dt>
                      <dd className="mt-1 font-medium text-ink">{formatCurrency(linkedAccount.balance)}</dd>
                    </div>
                  </dl>
                  <NavigatingLink href={`/accounts/${linkedAccount.id}`} className="mt-4 inline-flex min-h-9 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-mint">
                    Ver conta
                    <ArrowRight className="h-4 w-4" />
                  </NavigatingLink>
                </>
              ) : (
                <p className="mt-2 text-sm text-stone-500">Nenhuma conta vinculada a este cartao.</p>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Proximas faturas</h2>
            <p className="mt-1 text-xs text-stone-500">Faturas abertas ou vencidas deste cartao.</p>
          </div>
          <div className="divide-y divide-stone-100">
            {summary.upcoming_statements.map((statement) => (
              <Link key={statement.id} href={`/statements/${statement.id}`} className="grid gap-3 px-5 py-4 hover:bg-stone-50 sm:grid-cols-[1fr_auto]">
                <div className="min-w-0">
                  <p className="font-medium text-ink">Referencia {formatDate(statement.reference_month)}</p>
                  <p className="mt-1 text-xs text-stone-500">
                    Vencimento {statement.due_date ? formatDate(statement.due_date) : "-"} - {translateStatementStatus(statement.status)}
                  </p>
                  <span className={`mt-2 inline-flex rounded-md px-2 py-1 text-xs font-medium ${integrityClass(statement.integrity_status)}`}>
                    {statement.integrity_status === "difference" ? "Divergencia" : statement.integrity_status === "no_transactions" ? "Sem transacoes" : "OK"}
                  </span>
                </div>
                <p className="text-left font-semibold text-ink sm:text-right">{formatCurrency(statementAmount(statement))}</p>
              </Link>
            ))}
            {summary.upcoming_statements.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-stone-500">Nenhuma fatura encontrada.</p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="max-w-full overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Historico de faturas</h2>
            <p className="mt-1 text-xs text-stone-500">Ultimas 12 faturas do cartao.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] table-fixed divide-y divide-stone-200 text-sm">
              <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
                <tr>
                  <th className="w-[108px] px-4 py-3">Referencia</th>
                  <th className="w-[108px] px-4 py-3">Vencimento</th>
                  <th className="px-4 py-3 text-right">Informado</th>
                  <th className="px-4 py-3 text-right">Calculado</th>
                  <th className="px-4 py-3 text-right">Diferenca</th>
                  <th className="w-[104px] px-4 py-3">Status</th>
                  <th className="w-[116px] px-4 py-3">Integridade</th>
                  <th className="w-[104px] px-4 py-3 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {summary.statement_history.map((statement) => (
                  <tr key={statement.id} className="hover:bg-stone-50">
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">{formatDate(statement.reference_month)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">{statement.due_date ? formatDate(statement.due_date) : "-"}</td>
                    <td className="px-4 py-3 text-right text-stone-600">{statement.reported_total ? formatCurrency(statement.reported_total) : "-"}</td>
                    <td className="px-4 py-3 text-right text-stone-600">{formatCurrency(statement.calculated_total)}</td>
                    <td className="px-4 py-3 text-right text-stone-600">{statement.difference ? formatCurrency(statement.difference) : "-"}</td>
                    <td className="px-4 py-3 text-stone-600">{translateStatementStatus(statement.status)}</td>
                    <td className="px-4 py-3">
                      <span className={`whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium ${integrityClass(statement.integrity_status)}`}>
                        {statement.integrity_status === "difference" ? "Divergencia" : statement.integrity_status === "no_transactions" ? "Sem transacoes" : "OK"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/statements/${statement.id}`} className="inline-flex min-h-9 items-center justify-center whitespace-nowrap rounded-md border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-mint">
                        Ver fatura
                      </Link>
                    </td>
                  </tr>
                ))}
                {summary.statement_history.length === 0 ? (
                  <tr>
                    <td className="px-4 py-8 text-center text-stone-500" colSpan={8}>Nenhuma fatura encontrada.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <div className="max-w-full overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-100 px-5 py-4">
            <div>
              <h2 className="text-base font-semibold text-ink">Ultimas transacoes</h2>
              <p className="mt-1 text-xs text-stone-500">Ultimos lancamentos vinculados ao cartao.</p>
            </div>
            <Link href={`/transactions?card_id=${summary.card.id}`} className="inline-flex min-h-9 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-mint">
              Ver transacoes filtradas
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] table-fixed divide-y divide-stone-200 text-sm">
              <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
                <tr>
                  <th className="w-[104px] px-4 py-3">Data</th>
                  <th className="px-4 py-3">Descricao</th>
                  <th className="w-[140px] px-4 py-3">Categoria</th>
                  <th className="w-[112px] px-4 py-3 text-right">Valor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {summary.recent_transactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-stone-50">
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">{formatDate(transaction.transaction_date)}</td>
                    <td className="truncate px-4 py-3 font-medium text-ink" title={transaction.description}>
                      <span className="block truncate">{transaction.description}</span>
                      <span className="mt-1 block text-xs font-normal text-stone-500">{translateTransactionType(transaction.type)}</span>
                    </td>
                    <td className="truncate px-4 py-3 text-stone-600">{getCategoryName(transaction.category_id, categories)}</td>
                    <td className="px-4 py-3 text-right font-medium text-ink">{formatCurrency(transaction.amount)}</td>
                  </tr>
                ))}
                {summary.recent_transactions.length === 0 ? (
                  <tr>
                    <td className="px-4 py-8 text-center text-stone-500" colSpan={4}>Nenhuma transacao vinculada.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
