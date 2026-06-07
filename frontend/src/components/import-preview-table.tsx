"use client";

import { useMemo, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { confirmImport } from "@/lib/api";
import type { Category, ImportPreviewItem, TransactionType } from "@/lib/types";

interface EditableItem extends ImportPreviewItem {
  selected: boolean;
}

interface ImportPreviewTableProps {
  importId: string;
  items: ImportPreviewItem[];
  categories: Category[];
}

const transactionTypes: TransactionType[] = ["expense", "income", "transfer", "payment", "refund"];

export function ImportPreviewTable({ importId, items, categories }: ImportPreviewTableProps) {
  const [rows, setRows] = useState<EditableItem[]>(items.map((item) => ({ ...item, selected: !item.duplicate_candidate })));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const selectedCount = useMemo(() => rows.filter((item) => item.selected).length, [rows]);

  function updateRow(id: string, patch: Partial<EditableItem>) {
    setRows((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function handleConfirm() {
    setSaving(true);
    setMessage(null);
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
      await confirmImport(importId, payload);
      setMessage("Transações selecionadas adicionadas.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao confirmar importação.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-stone-600">{selectedCount} de {rows.length} selecionadas</p>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={saving || rows.length === 0}
          className="inline-flex items-center gap-2 rounded-md bg-mint px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Adicionar selecionadas
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="min-w-full divide-y divide-stone-200 text-sm">
          <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
            <tr>
              <th className="px-3 py-3">Sel.</th>
              <th className="px-3 py-3">Data</th>
              <th className="px-3 py-3">Descrição</th>
              <th className="px-3 py-3">Categoria</th>
              <th className="px-3 py-3">Tipo</th>
              <th className="px-3 py-3">Valor</th>
              <th className="px-3 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2">
                  <input type="checkbox" checked={row.selected} onChange={(event) => updateRow(row.id, { selected: event.target.checked })} />
                </td>
                <td className="px-3 py-2">
                  <input className="w-32 rounded-md border border-stone-200 px-2 py-1" type="date" value={row.transaction_date} onChange={(event) => updateRow(row.id, { transaction_date: event.target.value })} />
                </td>
                <td className="px-3 py-2">
                  <input className="w-64 rounded-md border border-stone-200 px-2 py-1" value={row.description} onChange={(event) => updateRow(row.id, { description: event.target.value })} />
                </td>
                <td className="px-3 py-2">
                  <select className="w-44 rounded-md border border-stone-200 px-2 py-1" value={row.category_id ?? ""} onChange={(event) => updateRow(row.id, { category_id: event.target.value || null })}>
                    <option value="">Sem categoria</option>
                    {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <select className="w-32 rounded-md border border-stone-200 px-2 py-1" value={row.type} onChange={(event) => updateRow(row.id, { type: event.target.value as TransactionType })}>
                    {transactionTypes.map((type) => <option key={type} value={type}>{type}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input className="w-28 rounded-md border border-stone-200 px-2 py-1 text-right" value={row.amount} onChange={(event) => updateRow(row.id, { amount: event.target.value })} />
                </td>
                <td className="px-3 py-2">
                  <span className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-700">{row.duplicate_candidate ? "duplicate" : row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {message ? <p className="rounded-md bg-white px-3 py-2 text-sm text-ink">{message}</p> : null}
    </div>
  );
}
