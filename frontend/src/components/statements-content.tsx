"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";
import { StatementDeleteButton } from "@/components/statement-delete-button";
import { StatementStatusButton } from "@/components/statement-status-button";
import { formatCurrency, formatDate } from "@/lib/format";
import { formatCardName, getAccountName, translateStatementStatus } from "@/lib/labels";
import type { Account, Card, CardStatementSummary } from "@/lib/types";

type StatementFilter = "all" | "ok" | "difference" | "no_transactions" | "paid";

interface StatementsContentProps {
  statements: CardStatementSummary[];
  accounts: Account[];
  cards: Card[];
}

const filterLabels: Record<StatementFilter, string> = {
  all: "Todas",
  ok: "OK",
  difference: "Divergência",
  no_transactions: "Sem transações",
  paid: "Pagas"
};

function hasDifference(statement: CardStatementSummary) {
  return statement.difference !== null && Math.abs(Number(statement.difference)) > 0.009;
}

function sortByUsefulDueDate(statements: CardStatementSummary[]) {
  const today = new Date().toISOString().slice(0, 10);
  const withDueDate = statements.filter((statement) => statement.due_date);
  const future = withDueDate
    .filter((statement) => statement.due_date! >= today)
    .sort((a, b) => a.due_date!.localeCompare(b.due_date!));
  const past = withDueDate
    .filter((statement) => statement.due_date! < today)
    .sort((a, b) => b.due_date!.localeCompare(a.due_date!));
  const withoutDueDate = statements
    .filter((statement) => !statement.due_date)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  return [...future, ...past, ...withoutDueDate];
}

function integrityClass(status: CardStatementSummary["integrity_status"]) {
  if (status === "difference") return "bg-red-50 text-red-700";
  if (status === "no_transactions") return "bg-amber-50 text-amber-800";
  return "bg-emerald-50 text-emerald-700";
}

function matchesFilter(statement: CardStatementSummary, filter: StatementFilter) {
  if (filter === "all") return true;
  if (filter === "paid") return statement.status === "paid";
  return statement.integrity_status === filter;
}

export function StatementsContent({ statements, accounts, cards }: StatementsContentProps) {
  const [filter, setFilter] = useState<StatementFilter>("all");

  const counts = useMemo<Record<StatementFilter, number>>(
    () => ({
      all: statements.length,
      ok: statements.filter((statement) => statement.integrity_status === "ok").length,
      difference: statements.filter((statement) => statement.integrity_status === "difference").length,
      no_transactions: statements.filter((statement) => statement.integrity_status === "no_transactions").length,
      paid: statements.filter((statement) => statement.status === "paid").length
    }),
    [statements]
  );

  const sortedStatements = useMemo(
    () => sortByUsefulDueDate(statements.filter((statement) => matchesFilter(statement, filter))),
    [filter, statements]
  );

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">Cartões</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Faturas</h1>
        <p className="mt-2 text-sm text-stone-500">Acompanhe faturas agrupadas por cartão e confira diferenças entre total informado e calculado.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(filterLabels) as StatementFilter[]).map((key) => {
          const isActive = filter === key;
          return (
            <button
              key={key}
              className={`inline-flex min-h-9 items-center justify-center gap-2 whitespace-nowrap rounded-md border px-3 py-2 text-sm font-medium ${
                isActive ? "border-mint bg-mint text-white" : "border-stone-200 bg-white text-stone-700 hover:bg-stone-50"
              }`}
              onClick={() => setFilter(key)}
              type="button"
            >
              <span>{filterLabels[key]}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${isActive ? "bg-white/20 text-white" : "bg-stone-100 text-stone-600"}`}>{counts[key]}</span>
            </button>
          );
        })}
      </div>

      <div className="grid gap-3 lg:hidden">
        {sortedStatements.map((statement) => {
          const card = cards.find((item) => item.id === statement.card_id);
          const differenceIsHighlighted = hasDifference(statement);
          return (
            <article key={statement.id} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="break-words font-semibold text-ink">{card ? formatCardName(card) : "Cartão não encontrado"}</p>
                  <p className="mt-1 break-words text-sm text-stone-500">{getAccountName(statement.account_id, accounts)}</p>
                </div>
                <span className={`shrink-0 whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium ${integrityClass(statement.integrity_status)}`}>
                  {statement.integrity_label}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs uppercase text-stone-400">Referência</p>
                  <p className="font-medium text-stone-700">{formatDate(statement.reference_month)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-stone-400">Vencimento</p>
                  <p className="font-medium text-stone-700">{statement.due_date ? formatDate(statement.due_date) : "-"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-stone-400">Informado</p>
                  <p className="font-medium text-stone-700">{statement.reported_total ? formatCurrency(statement.reported_total) : "-"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-stone-400">Calculado</p>
                  <p className="font-medium text-stone-700">{formatCurrency(statement.calculated_total)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-stone-400">Diferença</p>
                  <p className={`font-medium ${differenceIsHighlighted ? "text-coral" : "text-stone-700"}`}>{statement.difference ? formatCurrency(statement.difference) : "-"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-stone-400">Status</p>
                  <p className="font-medium text-stone-700">{translateStatementStatus(statement.status)}</p>
                </div>
              </div>

              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <StatementStatusButton compact statementId={statement.id} status={statement.status} />
                {statement.integrity_status === "no_transactions" ? (
                  <StatementDeleteButton compact statementId={statement.id} />
                ) : null}
                {card ? (
                  <Link href={`/cards/${card.id}`} className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-2.5 py-2 text-sm font-medium text-mint">
                    Ver cartão
                  </Link>
                ) : null}
                <Link href={`/statements/${statement.id}`} className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-2.5 py-2 text-sm font-medium text-mint">
                  Detalhes
                  <ArrowRight className="h-4 w-4 shrink-0" />
                </Link>
              </div>
            </article>
          );
        })}
        {sortedStatements.length === 0 ? (
          <div className="rounded-lg border border-stone-200 bg-white px-4 py-8 text-center text-sm text-stone-500 shadow-sm">Nenhuma fatura encontrada para este filtro.</div>
        ) : null}
      </div>

      <div className="hidden overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm lg:block">
        <div className="overflow-x-auto">
          <table className="min-w-[972px] table-fixed divide-y divide-stone-200 text-sm">
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="w-[220px] px-4 py-3">Cartão e conta</th>
                <th className="w-[105px] px-4 py-3">Referência</th>
                <th className="w-[105px] px-4 py-3">Vencimento</th>
                <th className="px-4 py-3 text-right">Totais</th>
                <th className="w-[112px] px-4 py-3">Integridade</th>
                <th className="w-[100px] px-4 py-3">Status</th>
                <th className="w-[220px] px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {sortedStatements.map((statement) => {
                const card = cards.find((item) => item.id === statement.card_id);
                const differenceIsHighlighted = hasDifference(statement);
                return (
                  <tr key={statement.id} className="hover:bg-stone-50">
                    <td className="px-4 py-3">
                      <p className="break-words font-medium text-ink">{card ? formatCardName(card) : "Cartão não encontrado"}</p>
                      <p className="mt-1 break-words text-xs text-stone-500">{getAccountName(statement.account_id, accounts)}</p>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">{formatDate(statement.reference_month)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">{statement.due_date ? formatDate(statement.due_date) : "-"}</td>
                    <td className="px-4 py-3 text-right text-stone-600">
                      <p>{statement.reported_total ? formatCurrency(statement.reported_total) : "-"}</p>
                      <p className="mt-1 text-xs text-stone-400">Calc. {formatCurrency(statement.calculated_total)}</p>
                      <p className={`mt-1 text-xs font-medium ${differenceIsHighlighted ? "text-coral" : "text-stone-500"}`}>Dif. {statement.difference ? formatCurrency(statement.difference) : "-"}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium ${integrityClass(statement.integrity_status)}`}>
                        {statement.integrity_label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      <p>{translateStatementStatus(statement.status)}</p>
                      <p className="mt-1 text-xs text-stone-400">{statement.transaction_count} transações</p>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="grid justify-end gap-2">
                        <StatementStatusButton compact statementId={statement.id} status={statement.status} />
                        {statement.integrity_status === "no_transactions" ? (
                          <StatementDeleteButton compact statementId={statement.id} />
                        ) : null}
                        {card ? (
                          <Link href={`/cards/${card.id}`} className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-2.5 py-2 text-sm font-medium text-mint">
                            Ver cartão
                          </Link>
                        ) : null}
                        <Link href={`/statements/${statement.id}`} className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-stone-200 bg-white px-2.5 py-2 text-sm font-medium text-mint">
                          Detalhes
                          <ArrowRight className="h-4 w-4 shrink-0" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {sortedStatements.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-stone-500" colSpan={7}>Nenhuma fatura encontrada para este filtro.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
