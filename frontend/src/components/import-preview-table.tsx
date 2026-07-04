"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Loader2 } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { confirmImport } from "@/lib/api";
import { formatAccountName, formatCardWithAccount, translateTransactionType } from "@/lib/labels";
import type { Account, Card, Category, ImportPreviewItem, TransactionType } from "@/lib/types";

interface EditableItem extends ImportPreviewItem {
  selected: boolean;
}

interface ImportPreviewTableProps {
  importId: string;
  items: ImportPreviewItem[];
  categories: Category[];
  accounts: Account[];
  cards: Card[];
}

const transactionTypes: TransactionType[] = ["expense", "income", "transfer", "payment", "refund"];

export function ImportPreviewTable({ importId, items, categories, accounts, cards }: ImportPreviewTableProps) {
  const router = useRouter();
  const cardsWithAccount = cards.filter((card) => Boolean(card.account_id));
  const suggestedCard = cardsWithAccount.find((card) => items.some((item) => item.card_last_digits === card.last_digits));
  const suggestedAccount = accounts.find((account) =>
    items.some((item) => {
      if (item.account_agency && item.account_number) {
        return account.agency === item.account_agency && account.account_number === item.account_number;
      }
      if (item.account_number) return account.account_number === item.account_number;
      return false;
    })
  );
  const [rows, setRows] = useState<EditableItem[]>(
    items.map((item) => {
      const card = cardsWithAccount.find((candidate) => candidate.id === item.card_id) ?? suggestedCard;
      return {
        ...item,
        account_id: item.account_id ?? card?.account_id ?? suggestedAccount?.id ?? null,
        card_id: item.card_id ?? card?.id ?? null,
        selected: item.default_selected
      };
    })
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<"success" | "error" | null>(null);

  const selectedCount = useMemo(() => rows.filter((item) => item.selected).length, [rows]);
  const selectedTotal = useMemo(
    () => rows.filter((item) => item.selected).reduce((total, item) => total + Number(item.amount), 0),
    [rows]
  );

  function updateRow(id: string, patch: Partial<EditableItem>) {
    setRows((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  function isBulkConfirmable(item: EditableItem) {
    return !item.duplicate_candidate && !item.needs_review && item.type !== "payment" && item.type !== "refund";
  }

  function selectAllConfirmable() {
    setRows((current) => current.map((item) => ({ ...item, selected: isBulkConfirmable(item) })));
  }

  function unselectAll() {
    setRows((current) => current.map((item) => ({ ...item, selected: false })));
  }

  function applyAccount(accountId: string) {
    setRows((current) => current.map((item) => (item.selected ? { ...item, account_id: accountId || null, card_id: null } : item)));
  }

  function applyCard(cardId: string) {
    const card = cardsWithAccount.find((item) => item.id === cardId);
    setRows((current) =>
      current.map((item) =>
        item.selected ? { ...item, card_id: card?.id ?? null, account_id: card?.account_id ?? null } : item
      )
    );
  }

  async function handleConfirm() {
    setSaving(true);
    setMessage(null);
    setMessageType(null);
    try {
      const payload = rows.map((row) => ({
        preview_item_id: row.id,
        selected: row.selected,
        transaction_date: row.transaction_date,
        description: row.description,
        amount: row.amount,
        type: row.type,
        category_id: row.category_id,
        account_id: row.account_id,
        card_id: row.card_id,
        card_statement_id: row.card_statement_id,
        installment_current: row.installment_current,
        installment_total: row.installment_total
      }));
      const response = await confirmImport(importId, payload);
      setMessage(`${response.created_transaction_ids.length} transações adicionadas. Abrindo listagem...`);
      setMessageType("success");
      router.push("/transactions");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao confirmar importação.");
      setMessageType("error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-stone-600">
          {selectedCount} de {rows.length} selecionadas · Total selecionado R$ {selectedTotal.toFixed(2)}
        </p>
        <div className="flex flex-wrap gap-2">
          <UiButton onClick={selectAllConfirmable} size="sm" variant="secondary">
            Selecionar todos
          </UiButton>
          <UiButton onClick={unselectAll} size="sm" variant="secondary">
            Desmarcar todos
          </UiButton>
          <UiButton
            onClick={handleConfirm}
            disabled={saving || rows.length === 0}
            icon={saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            size="sm"
            variant="primary"
          >
            Adicionar selecionadas
          </UiButton>
        </div>
      </div>

      {(accounts.length > 0 || cardsWithAccount.length > 0) ? (
        <div className="grid gap-3 rounded-lg border border-stone-200 bg-white p-4 shadow-sm lg:grid-cols-2">
          <label className="space-y-2">
            <span className="block text-sm font-medium text-ink">Aplicar cartão a todas as transações selecionadas</span>
            <select className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" defaultValue={suggestedCard?.id ?? ""} onChange={(event) => applyCard(event.target.value)}>
              <option value="">Nenhum cartão</option>
              {cardsWithAccount.map((card) => <option key={card.id} value={card.id}>{formatCardWithAccount(card, accounts)}</option>)}
            </select>
          </label>
          <label className="space-y-2">
            <span className="block text-sm font-medium text-ink">Aplicar conta a todas as transações selecionadas</span>
            <select className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" defaultValue={suggestedAccount?.id ?? ""} onChange={(event) => applyAccount(event.target.value)}>
              <option value="">Nenhuma conta</option>
              {accounts.map((account) => <option key={account.id} value={account.id}>{formatAccountName(account)}</option>)}
            </select>
          </label>
          {suggestedCard ? <p className="text-xs text-stone-500 lg:col-span-2">Cartão sugerido pelos últimos 4 dígitos detectados na fatura: {formatCardWithAccount(suggestedCard, accounts)}.</p> : null}
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="min-w-full divide-y divide-stone-200 text-sm">
          <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
            <tr>
              <th className="px-3 py-3">Sel.</th>
              <th className="px-3 py-3">Data</th>
              <th className="px-3 py-3">Descrição</th>
              <th className="px-3 py-3">Sugestão</th>
              <th className="px-3 py-3">Regra</th>
              <th className="px-3 py-3">País</th>
              <th className="px-3 py-3">Parcela</th>
              <th className="px-3 py-3">Categoria</th>
              <th className="px-3 py-3">Tipo</th>
              <th className="px-3 py-3">Valor</th>
              <th className="px-3 py-3">Confiança</th>
              <th className="px-3 py-3">Motivo</th>
              <th className="px-3 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {rows.map((row) => (
              <tr key={row.id} className={row.needs_review ? "bg-amber-50" : undefined}>
                <td className="px-3 py-2">
                  <input type="checkbox" checked={row.selected} onChange={(event) => updateRow(row.id, { selected: event.target.checked })} />
                </td>
                <td className="px-3 py-2">
                  <input
                    className="w-32 rounded-md border border-stone-200 px-2 py-1"
                    type="date"
                    value={row.transaction_date}
                    onInput={(event) => updateRow(row.id, { transaction_date: event.currentTarget.value })}
                    onChange={(event) => updateRow(row.id, { transaction_date: event.target.value })}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    className="w-64 rounded-md border border-stone-200 px-2 py-1"
                    value={row.description}
                    onInput={(event) => updateRow(row.id, { description: event.currentTarget.value })}
                    onChange={(event) => updateRow(row.id, { description: event.target.value })}
                  />
                </td>
                <td className="px-3 py-2 text-stone-700">{row.suggested_category ?? "-"}</td>
                <td className="px-3 py-2 text-stone-700">
                  {row.classification_label ? (
                    <span className={row.needs_review && row.suggested_category ? "rounded-md bg-amber-100 px-2 py-1 text-xs text-amber-800" : undefined}>
                      {row.classification_label}
                    </span>
                  ) : "-"}
                </td>
                <td className="px-3 py-2 text-stone-700">{row.merchant_country ?? "-"}</td>
                <td className="px-3 py-2 text-stone-700">
                  {row.installment_current && row.installment_total ? `${row.installment_current}/${row.installment_total}` : "-"}
                </td>
                <td className="px-3 py-2">
                  <select className="w-44 rounded-md border border-stone-200 px-2 py-1" value={row.category_id ?? ""} onChange={(event) => updateRow(row.id, { category_id: event.target.value || null })}>
                    <option value="">Sem categoria</option>
                    {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <select className="w-32 rounded-md border border-stone-200 px-2 py-1" value={row.type} onChange={(event) => updateRow(row.id, { type: event.target.value as TransactionType })}>
                    {transactionTypes.map((type) => <option key={type} value={type}>{translateTransactionType(type)}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input
                    className="w-28 rounded-md border border-stone-200 px-2 py-1 text-right"
                    value={row.amount}
                    onInput={(event) => updateRow(row.id, { amount: event.currentTarget.value })}
                    onChange={(event) => updateRow(row.id, { amount: event.target.value })}
                  />
                </td>
                <td className="px-3 py-2">
                  <span className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-700">{Math.round(row.parser_confidence * 100)}%</span>
                </td>
                <td className="px-3 py-2 text-stone-600">{row.excluded_reason ?? (row.needs_review ? "revisar" : "-")}</td>
                <td className="px-3 py-2">
                  <span className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-700">{row.duplicate_candidate ? "duplicate" : row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {message ? (
        <p className={`rounded-md px-3 py-2 text-sm ${messageType === "error" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
          {message}
        </p>
      ) : null}
    </div>
  );
}
