"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Plus, Save, X } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createClassificationRule } from "@/lib/api";
import { translateTransactionType } from "@/lib/labels";
import type { Category, ClassificationMatchScope, ClassificationRulePayload, TransactionType } from "@/lib/types";

interface ClassificationRuleDialogProps {
  categories: Category[];
  initialValues: ClassificationRulePayload | null;
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const emptyRule: ClassificationRulePayload = {
  keyword: "",
  category_id: "",
  transaction_type: "expense",
  priority: 100,
  status: "active",
  match_scope: "both",
  auto_created: false,
};

const matchScopeLabels: Record<ClassificationMatchScope, string> = {
  description: "Descricao editada",
  original_description: "Descricao original",
  both: "Ambas",
};

function withRuleCategory(payload: ClassificationRulePayload, categoryId: string): ClassificationRulePayload {
  return {
    ...payload,
    category_id: categoryId,
    actions: payload.actions?.map((action) => (
      action.type === "set_category" ? { ...action, category_id: categoryId } : action
    ))
  };
}

export function ClassificationRuleDialog({ categories, initialValues, open, onClose, onCreated }: ClassificationRuleDialogProps) {
  const toast = useToast();
  const firstFieldRef = useRef<HTMLInputElement | null>(null);
  const [form, setForm] = useState<ClassificationRulePayload>({ ...emptyRule, category_id: categories[0]?.id ?? "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const timeoutId = window.setTimeout(() => {
      setForm({
        ...emptyRule,
        category_id: categories[0]?.id ?? "",
        ...initialValues,
        keyword: initialValues?.keyword.toUpperCase() ?? "",
      });
      setError(null);
      firstFieldRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [categories, initialValues, open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !isSubmitting) onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isSubmitting, onClose, open]);

  if (!open) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await createClassificationRule({ ...form, keyword: form.keyword.toUpperCase(), auto_created: false });
      toast.success("Regra criada.");
      onCreated();
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao criar regra.";
      setError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <button className="absolute inset-0 bg-black/30" type="button" aria-label="Fechar criacao de regra" onClick={onClose} disabled={isSubmitting} />
      <section aria-labelledby="classification-rule-dialog-title" aria-modal="true" className="relative w-full max-w-2xl rounded-lg border border-stone-200 bg-white p-5 shadow-2xl" role="dialog">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-mint">Regra sugerida</p>
            <h2 id="classification-rule-dialog-title" className="mt-1 text-xl font-semibold text-ink">Revisar e adicionar regra</h2>
          </div>
          <button className="rounded-md border border-stone-200 p-2 text-stone-600 transition hover:bg-stone-50" type="button" onClick={onClose} aria-label="Fechar" disabled={isSubmitting}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
          {error ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1.5 text-sm font-medium text-stone-600">
              Palavra-chave
              <input
                ref={firstFieldRef}
                className="h-10 rounded-md border border-stone-200 px-3 text-sm uppercase text-ink outline-none focus:border-mint"
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, keyword: event.target.value.toUpperCase() }))}
                required
                value={form.keyword}
              />
            </label>
            <label className="grid gap-1.5 text-sm font-medium text-stone-600">
              Categoria
              <select className="h-10 rounded-md border border-stone-200 px-3 text-sm text-ink outline-none focus:border-mint" disabled={isSubmitting} onChange={(event) => setForm((current) => withRuleCategory(current, event.target.value))} required value={form.category_id}>
                {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </select>
            </label>
            <label className="grid gap-1.5 text-sm font-medium text-stone-600">
              Tipo
              <select className="h-10 rounded-md border border-stone-200 px-3 text-sm text-ink outline-none focus:border-mint" disabled={isSubmitting} onChange={(event) => setForm((current) => ({ ...current, transaction_type: (event.target.value || null) as TransactionType | null }))} value={form.transaction_type ?? ""}>
                <option value="expense">{translateTransactionType("expense")}</option>
                <option value="income">{translateTransactionType("income")}</option>
                <option value="">Ambas</option>
              </select>
            </label>
            <label className="grid gap-1.5 text-sm font-medium text-stone-600">
              Buscar em
              <select className="h-10 rounded-md border border-stone-200 px-3 text-sm text-ink outline-none focus:border-mint" disabled={isSubmitting} onChange={(event) => setForm((current) => ({ ...current, match_scope: event.target.value as ClassificationMatchScope }))} value={form.match_scope}>
                {Object.entries(matchScopeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <UiButton disabled={isSubmitting} onClick={onClose} type="button" variant="ghost">
              Cancelar
            </UiButton>
            <UiButton disabled={isSubmitting || !form.keyword || !form.category_id} icon={isSubmitting ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
              {isSubmitting ? "Salvando..." : "Adicionar regra"}
            </UiButton>
          </div>
        </form>
      </section>
    </div>
  );
}
