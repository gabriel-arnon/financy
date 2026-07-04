"use client";

import { FormEvent, ReactNode, useState } from "react";
import { ListChecks, Pencil, Plus, RefreshCw, Save, Trash2 } from "lucide-react";
import { IconButton, UiButton } from "@/components/ui-button";
import {
  createClassificationRule,
  deleteClassificationRule,
  getCategories,
  getClassificationRules,
  updateClassificationRule,
} from "@/lib/api";
import { getCategoryName, translateTransactionType } from "@/lib/labels";
import type {
  Category,
  ClassificationMatchScope,
  ClassificationRule,
  ClassificationRulePayload,
  TransactionType,
} from "@/lib/types";

interface RulesContentProps {
  initialRules: ClassificationRule[];
  initialCategories: Category[];
  embedded?: boolean;
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
  description: "Descrição editada",
  original_description: "Descrição original",
  both: "Ambas",
};

export function RulesContent({ initialRules, initialCategories, embedded = false }: RulesContentProps) {
  const [rules, setRules] = useState<ClassificationRule[]>(initialRules);
  const [categories, setCategories] = useState<Category[]>(initialCategories);
  const [form, setForm] = useState<ClassificationRulePayload>({ ...emptyRule, category_id: initialCategories[0]?.id ?? "" });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    const [nextRules, nextCategories] = await Promise.all([getClassificationRules(), getCategories()]);
    setRules(nextRules);
    setCategories(nextCategories);
    setForm((current) => ({ ...current, category_id: current.category_id || nextCategories[0]?.id || "" }));
  }

  async function handleReload() {
    setMessage(null);
    setError(null);
    try {
      await loadData();
      setMessage("Regras recarregadas.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao recarregar regras.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const payload = { ...form, keyword: form.keyword.toUpperCase(), auto_created: false };
      if (editingId) {
        await updateClassificationRule(editingId, payload);
        setMessage("Regra atualizada.");
      } else {
        await createClassificationRule(payload);
        setMessage("Regra criada.");
      }
      setForm({ ...emptyRule, category_id: categories[0]?.id ?? "" });
      setEditingId(null);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar regra.");
    }
  }

  function editRule(rule: ClassificationRule) {
    setEditingId(rule.id);
    setForm({
      keyword: rule.keyword,
      category_id: rule.category_id,
      transaction_type: rule.transaction_type,
      priority: rule.priority,
      status: "active",
      match_scope: rule.match_scope,
      auto_created: rule.auto_created,
    });
  }

  async function inactivateRule(ruleId: string) {
    if (!window.confirm("Inativar esta regra? Ela deixará de classificar lançamentos.")) return;
    setMessage(null);
    setError(null);
    try {
      await deleteClassificationRule(ruleId);
      setMessage("Regra inativada.");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao inativar regra.");
    }
  }

  function cancelEdit() {
    setEditingId(null);
    setForm({ ...emptyRule, category_id: categories[0]?.id ?? "" });
  }

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <ListChecks className={`${embedded ? "mt-0.5 h-5 w-5" : "mt-1 h-7 w-7"} text-mint`} />
        <div>
          {embedded ? (
            <h2 className="text-lg font-semibold text-ink">Regras de classificação</h2>
          ) : (
            <h1 className="text-3xl font-semibold text-ink">Regras</h1>
          )}
          <p className={`${embedded ? "mt-1" : "mt-2 font-medium"} text-sm text-stone-600`}>
            Classifique lançamentos automaticamente por palavras da descrição.
          </p>
        </div>
      </div>
      <UiButton icon={<RefreshCw className="h-4 w-4" />} onClick={handleReload} variant="secondary">
        Recarregar regras
      </UiButton>
    </div>
  );

  const content = (
    <>
      {message ? <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
      {error ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      <form
        className={embedded ? "rounded-md border border-stone-100 bg-stone-50 p-4" : "rounded-lg border border-stone-200 bg-white p-6 shadow-sm"}
        onSubmit={handleSubmit}
      >
        <div className="flex items-center gap-2">
          {editingId ? <Pencil className="h-5 w-5 text-mint" /> : <Plus className="h-5 w-5 text-mint" />}
          <h2 className="text-lg font-semibold text-ink">{editingId ? "Editar regra" : "Nova regra"}</h2>
        </div>
        <div className="mt-5 grid gap-3 lg:grid-cols-[1.4fr_1.2fr_1fr_1fr_0.7fr]">
          <input
            className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm uppercase outline-none focus:border-mint"
            onChange={(event) => setForm({ ...form, keyword: event.target.value.toUpperCase() })}
            placeholder="Keyword, ex: OPENAI"
            required
            value={form.keyword}
          />
          <select
            className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
            onChange={(event) => setForm({ ...form, category_id: event.target.value })}
            required
            value={form.category_id}
          >
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
          <select
            className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
            onChange={(event) => setForm({ ...form, transaction_type: (event.target.value || null) as TransactionType | null })}
            value={form.transaction_type ?? ""}
          >
            <option value="">Qualquer tipo</option>
            {(["expense", "income", "transfer", "payment", "refund"] as TransactionType[]).map((item) => (
              <option key={item} value={item}>
                {translateTransactionType(item)}
              </option>
            ))}
          </select>
          <select
            className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
            onChange={(event) => setForm({ ...form, match_scope: event.target.value as ClassificationMatchScope })}
            value={form.match_scope}
          >
            {Object.entries(matchScopeLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
            onChange={(event) => setForm({ ...form, priority: Number(event.target.value) })}
            type="number"
            value={form.priority}
          />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <UiButton icon={editingId ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
            {editingId ? "Salvar regra" : "Criar regra"}
          </UiButton>
          {editingId ? (
            <UiButton onClick={cancelEdit} variant="secondary">
              Cancelar
            </UiButton>
          ) : null}
        </div>
      </form>

      <article className={embedded ? "rounded-md border border-stone-100 bg-stone-50" : "rounded-lg border border-stone-200 bg-white shadow-sm"}>
        <div className="border-b border-stone-100 px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">Regras de classificação</h2>
          <p className="mt-1 text-sm text-stone-500">Regras ativas usadas para sugerir categorias nos lançamentos.</p>
        </div>
        <div className="divide-y divide-stone-100 p-4">
          {rules.map((rule) => (
            <div key={rule.id} className="grid gap-3 rounded-md px-2 py-3 sm:grid-cols-[1.1fr_1fr_0.9fr_0.5fr_auto] sm:items-center">
              <div>
                <p className="font-medium text-ink">{rule.keyword}</p>
                <p className="mt-1 text-xs text-stone-500">{rule.transaction_type ? translateTransactionType(rule.transaction_type) : "Qualquer tipo"}</p>
              </div>
              <p className="text-sm text-stone-600">{getCategoryName(rule.category_id, categories)}</p>
              <p className="text-sm text-stone-600">{matchScopeLabels[rule.match_scope]}</p>
              <p className="text-sm text-stone-600">Prioridade {rule.priority}</p>
              <div className="flex justify-start gap-2 sm:justify-end">
                <IconButton aria-label="Editar regra" icon={<Pencil className="h-4 w-4" />} onClick={() => editRule(rule)} title="Editar" variant="secondary" />
                <IconButton aria-label="Inativar regra" icon={<Trash2 className="h-4 w-4" />} onClick={() => inactivateRule(rule.id)} title="Excluir" variant="danger" />
              </div>
            </div>
          ))}
          {rules.length === 0 ? <p className="px-4 py-8 text-center text-sm text-stone-500">Nenhuma regra cadastrada.</p> : null}
        </div>
      </article>
    </>
  );

  if (embedded) {
    return (
      <article className="space-y-5 rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
        {header}
        {content}
      </article>
    );
  }

  return (
    <section className="space-y-6">
      {header}
      {content}
    </section>
  );
}
