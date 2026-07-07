"use client";

import { FormEvent, useEffect, useState } from "react";
import { ListChecks, Pencil, Plus, Save, Trash2 } from "lucide-react";
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
  skipInitialLoad?: boolean;
}

interface RuleFormProps {
  categories: Category[];
  form: ClassificationRulePayload;
  isEditing: boolean;
  isSubmitting: boolean;
  onCancel: () => void;
  onChange: (payload: ClassificationRulePayload) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

type RuleGroupKey = "income" | "expense" | "both";

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

const ruleGroups: Array<{ key: RuleGroupKey; title: string }> = [
  { key: "income", title: "Receitas" },
  { key: "expense", title: "Despesas" },
  { key: "both", title: "Ambas" },
];

function getRuleGroupKey(rule: ClassificationRule): RuleGroupKey {
  if (rule.transaction_type === "income") return "income";
  if (rule.transaction_type === "expense") return "expense";
  return "both";
}

function getRuleTypeLabel(rule: ClassificationRule) {
  return rule.transaction_type ? translateTransactionType(rule.transaction_type) : "Ambas";
}

function CountBadge({ count }: { count: number }) {
  return (
    <span className="rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-semibold text-stone-500">
      {count}
    </span>
  );
}

function RulesListLoading() {
  return (
    <div className="mt-5 space-y-5" aria-busy="true" aria-live="polite">
      {ruleGroups.map((group) => (
        <section key={group.key} className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-ink">{group.title}</h3>
            <span className="h-7 w-9 animate-pulse rounded-full bg-stone-100" />
          </div>
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-14 animate-pulse rounded-md bg-stone-100" />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function RuleForm({ categories, form, isEditing, isSubmitting, onCancel, onChange, onSubmit }: RuleFormProps) {
  return (
    <form className="rounded-md border border-stone-100 bg-stone-50 p-4" onSubmit={onSubmit}>
      <div className="flex items-center gap-2">
        {isEditing ? <Pencil className="h-5 w-5 text-mint" /> : <Plus className="h-5 w-5 text-mint" />}
        <h3 className="text-base font-semibold text-ink">{isEditing ? "Editar regra" : "Nova regra"}</h3>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[1.3fr_1.2fr_160px_160px_120px]">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Palavra-chave</span>
          <input
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm uppercase text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, keyword: event.target.value.toUpperCase() })}
            placeholder="Ex: OPENAI"
            required
            value={form.keyword}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Categoria</span>
          <select
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, category_id: event.target.value })}
            required
            value={form.category_id}
          >
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Tipo</span>
          <select
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, transaction_type: (event.target.value || null) as TransactionType | null })}
            value={form.transaction_type ?? ""}
          >
            <option value="expense">Despesa</option>
            <option value="income">Receita</option>
            <option value="">Ambas</option>
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Buscar em</span>
          <select
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, match_scope: event.target.value as ClassificationMatchScope })}
            value={form.match_scope}
          >
            {Object.entries(matchScopeLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Prioridade</span>
          <input
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, priority: Number(event.target.value) })}
            type="number"
            value={form.priority}
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <UiButton disabled={isSubmitting} icon={isEditing ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
          {isEditing ? "Salvar regra" : "Criar regra"}
        </UiButton>
        <UiButton disabled={isSubmitting} onClick={onCancel} variant="secondary">
          Cancelar
        </UiButton>
      </div>
    </form>
  );
}

export function RulesContent({ initialRules, initialCategories, embedded = false, skipInitialLoad = false }: RulesContentProps) {
  const [rules, setRules] = useState<ClassificationRule[]>(initialRules);
  const [categories, setCategories] = useState<Category[]>(initialCategories);
  const [form, setForm] = useState<ClassificationRulePayload>({ ...emptyRule, category_id: initialCategories[0]?.id ?? "" });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState<ClassificationRule | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(!skipInitialLoad);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    const [nextRules, nextCategories] = await Promise.all([getClassificationRules(), getCategories()]);
    setRules(nextRules);
    setCategories(nextCategories);
    setForm((current) => ({ ...current, category_id: current.category_id || nextCategories[0]?.id || "" }));
  }

  useEffect(() => {
    if (skipInitialLoad) return;
    void Promise.resolve()
      .then(loadData)
      .catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar regras."))
      .finally(() => setIsLoading(false));
  }, [skipInitialLoad]);

  function startCreate() {
    setMessage(null);
    setError(null);
    setEditingId(null);
    setConfirmingDelete(null);
    setForm({ ...emptyRule, category_id: categories[0]?.id ?? "" });
    setShowCreateForm(true);
  }

  function editRule(rule: ClassificationRule) {
    setMessage(null);
    setError(null);
    setShowCreateForm(false);
    setConfirmingDelete(null);
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

  function cancelEdit() {
    setEditingId(null);
    setShowCreateForm(false);
    setForm({ ...emptyRule, category_id: categories[0]?.id ?? "" });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    setIsSubmitting(true);

    try {
      const payload = { ...form, keyword: form.keyword.toUpperCase(), auto_created: false };
      if (editingId) {
        await updateClassificationRule(editingId, payload);
        setMessage("Regra atualizada.");
      } else {
        await createClassificationRule(payload);
        setMessage("Regra criada.");
      }
      await loadData();
      cancelEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar regra.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function confirmDelete() {
    if (!confirmingDelete) return;

    setMessage(null);
    setError(null);
    setIsSubmitting(true);

    try {
      await deleteClassificationRule(confirmingDelete.id);
      await loadData();
      if (editingId === confirmingDelete.id) {
        cancelEdit();
      }
      setConfirmingDelete(null);
      setMessage("Regra inativada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao inativar regra.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const header = (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <ListChecks className="h-5 w-5 text-mint" />
        {embedded ? (
          <h2 className="text-lg font-semibold text-ink">Regras de classificacao</h2>
        ) : (
          <h1 className="text-lg font-semibold text-ink">Regras de classificacao</h1>
        )}
      </div>
      <UiButton disabled={isSubmitting} icon={<Plus className="h-4 w-4" />} onClick={startCreate} variant="primary">
        Adicionar regra
      </UiButton>
    </div>
  );

  const content = (
    <>
      <p className="mt-4 text-sm leading-6 text-stone-600">
        Regras ativas usadas para sugerir categorias automaticamente nos lancamentos.
      </p>

      {message ? <p className="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
      {error ? <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      {showCreateForm ? (
        <div className="mt-5">
          <RuleForm
            categories={categories}
            form={form}
            isEditing={false}
            isSubmitting={isSubmitting}
            onCancel={cancelEdit}
            onChange={setForm}
            onSubmit={handleSubmit}
          />
        </div>
      ) : null}

      {isLoading ? (
        <RulesListLoading />
      ) : (
        <div className="mt-5 space-y-5">
          {ruleGroups.map((group) => {
            const groupRules = rules.filter((rule) => getRuleGroupKey(rule) === group.key);

            return (
              <section key={group.key} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-ink">{group.title}</h3>
                  <CountBadge count={groupRules.length} />
                </div>
                <div className="space-y-2">
                  {groupRules.length === 0 ? (
                    <p className="rounded-md border border-stone-100 bg-stone-50 px-4 py-6 text-center text-sm text-stone-500">
                      Nenhuma regra neste grupo.
                    </p>
                  ) : null}

                  {groupRules.map((rule) =>
                    editingId === rule.id ? (
                      <RuleForm
                        key={rule.id}
                        categories={categories}
                        form={form}
                        isEditing
                        isSubmitting={isSubmitting}
                        onCancel={cancelEdit}
                        onChange={setForm}
                        onSubmit={handleSubmit}
                      />
                    ) : (
                      <div key={rule.id} className="flex items-center justify-between gap-3 rounded-md border border-stone-100 bg-stone-50 px-4 py-3">
                        <div className="min-w-0">
                          <span className="block truncate text-sm font-medium text-ink">{rule.keyword}</span>
                          <span className="mt-1 block text-xs text-stone-500">{getCategoryName(rule.category_id, categories)}</span>
                        </div>

                        <div className="flex shrink-0 items-center gap-2">
                          <span className="rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-medium text-stone-500">
                            {getRuleTypeLabel(rule)}
                          </span>
                          <span className="hidden rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-medium text-stone-500 sm:inline-flex">
                            {matchScopeLabels[rule.match_scope]}
                          </span>
                          <span className="hidden rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-medium text-stone-500 sm:inline-flex">
                            Prioridade {rule.priority}
                          </span>
                          <IconButton
                            aria-label={`Editar regra ${rule.keyword}`}
                            disabled={isSubmitting}
                            icon={<Pencil className="h-4 w-4" />}
                            onClick={() => editRule(rule)}
                            title="Editar"
                            variant="secondary"
                          />
                          <IconButton
                            aria-label={`Inativar regra ${rule.keyword}`}
                            disabled={isSubmitting}
                            icon={<Trash2 className="h-4 w-4" />}
                            onClick={() => {
                              setMessage(null);
                              setError(null);
                              setConfirmingDelete(rule);
                            }}
                            title="Excluir"
                            variant="danger"
                          />
                        </div>
                      </div>
                    )
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </>
  );

  const wrapperClassName = embedded
    ? "space-y-5 rounded-lg border border-stone-200 bg-white p-6 shadow-sm"
    : "space-y-5 rounded-lg border border-stone-200 bg-white p-6 shadow-sm";

  return (
    <>
      <article className={wrapperClassName}>
        {header}
        {content}
      </article>

      {confirmingDelete ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4 py-6">
          <div className="w-full max-w-md rounded-lg border border-stone-200 bg-white p-5 shadow-xl">
            <h3 className="text-lg font-semibold text-ink">Inativar regra?</h3>
            <div className="mt-3 space-y-2 text-sm leading-6 text-stone-600">
              <p>A regra deixara de classificar automaticamente novos lancamentos.</p>
              <p>As transacoes ja classificadas serao preservadas.</p>
            </div>
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <UiButton disabled={isSubmitting} onClick={() => setConfirmingDelete(null)} variant="secondary">
                Cancelar
              </UiButton>
              <UiButton disabled={isSubmitting} onClick={confirmDelete} variant="danger">
                Inativar regra
              </UiButton>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
