import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { StatementStatusButton } from "@/components/statement-status-button";
import { serverGetAccounts, serverGetCards, serverGetCategories, serverGetStatement } from "@/lib/server-api";
import { formatCurrency, formatDate } from "@/lib/format";
import { formatCardWithAccount, getAccountName, getCategoryName, translateStatementStatus, translateTransactionType } from "@/lib/labels";

interface StatementDetailPageProps {
  params: Promise<{ statementId: string }>;
}

export const dynamic = "force-dynamic";

export default async function StatementDetailPage({ params }: StatementDetailPageProps) {
  const { statementId } = await params;
  const [statement, accounts, cards, categories] = await Promise.all([
    serverGetStatement(statementId).catch(() => null),
    serverGetAccounts().catch(() => []),
    serverGetCards().catch(() => []),
    serverGetCategories().catch(() => [])
  ]);

  if (!statement) {
    notFound();
  }

  const card = cards.find((item) => item.id === statement.card_id);
  const hasDifference = statement.difference !== null && Math.abs(Number(statement.difference)) > 0.009;
  const integrityTone = statement.integrity_status === "difference" ? "border-red-200 bg-red-50 text-red-800" : statement.integrity_status === "no_transactions" ? "border-amber-200 bg-amber-50 text-amber-800" : "border-emerald-200 bg-emerald-50 text-emerald-800";

  return (
    <section className="space-y-6">
      <div>
        <Link href="/statements" className="inline-flex items-center gap-2 text-sm font-medium text-mint">
          <ArrowLeft className="h-4 w-4" />
          Voltar para faturas
        </Link>
        <h1 className="mt-3 text-3xl font-semibold text-ink">Detalhes da fatura</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <p className="text-sm text-stone-500">{card ? formatCardWithAccount(card, accounts) : "Cartão não encontrado"}</p>
          <Link href={`/transactions?card_statement_id=${statement.id}`} className="inline-flex items-center rounded-md border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-mint shadow-sm">
            Ver transações filtradas
          </Link>
          <StatementStatusButton statementId={statement.id} status={statement.status} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Conta vinculada</p>
          <p className="mt-2 font-semibold text-ink">{getAccountName(statement.account_id, accounts)}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Mês de referência</p>
          <p className="mt-2 font-semibold text-ink">{formatDate(statement.reference_month)}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Vencimento</p>
          <p className="mt-2 font-semibold text-ink">{statement.due_date ? formatDate(statement.due_date) : "-"}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Status</p>
          <p className="mt-2 font-semibold text-ink">{translateStatementStatus(statement.status)}</p>
          {statement.paid_at ? <p className="mt-1 text-xs text-stone-500">Paga em {formatDate(statement.paid_at.slice(0, 10))}</p> : null}
        </div>
      </div>

      <div className={`rounded-lg border px-5 py-4 shadow-sm ${integrityTone}`}>
        <p className="text-sm font-semibold">Integridade: {statement.integrity_label}</p>
        {statement.integrity_status === "no_transactions" ? (
          <p className="mt-1 text-sm">Esta fatura não possui lançamentos vinculados.</p>
        ) : null}
        {statement.integrity_status === "difference" ? (
          <p className="mt-1 text-sm">O total informado no PDF é diferente da soma das transações.</p>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Total informado no PDF</p>
          <p className="mt-2 text-xl font-semibold text-ink">{statement.reported_total ? formatCurrency(statement.reported_total) : "-"}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Total calculado</p>
          <p className="mt-2 text-xl font-semibold text-ink">{formatCurrency(statement.calculated_total)}</p>
        </div>
        <div className={`rounded-lg border bg-white p-5 shadow-sm ${hasDifference ? "border-coral/40" : "border-stone-200"}`}>
          <p className="text-sm text-stone-500">Diferença</p>
          <p className={`mt-2 text-xl font-semibold ${hasDifference ? "text-coral" : "text-ink"}`}>{statement.difference ? formatCurrency(statement.difference) : "-"}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="border-b border-stone-100 px-5 py-4">
          <h2 className="text-base font-semibold text-ink">Transações vinculadas</h2>
          <p className="mt-1 text-xs text-stone-500">{statement.transaction_count} lançamentos nesta fatura.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-200 text-sm">
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3">Descrição</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3 text-right">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {statement.transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="whitespace-nowrap px-4 py-3 text-stone-600">{formatDate(transaction.transaction_date)}</td>
                  <td className="px-4 py-3 font-medium text-ink">{transaction.description}</td>
                  <td className="px-4 py-3 text-stone-600">{translateTransactionType(transaction.type)}</td>
                  <td className="px-4 py-3 text-stone-600">{getCategoryName(transaction.category_id, categories)}</td>
                  <td className="px-4 py-3 text-right font-medium text-ink">{formatCurrency(transaction.amount)}</td>
                </tr>
              ))}
              {statement.transactions.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-stone-500" colSpan={5}>Nenhuma transação vinculada.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
