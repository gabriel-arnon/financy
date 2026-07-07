"use client";

import { FormEvent, useEffect, useState } from "react";
import { Pencil, Plus, Save, Tags, Trash2 } from "lucide-react";
import { IconButton, UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createCategory, deleteCategory, getCategories, updateCategory } from "@/lib/api";
import type { Category, CategoryPayload, CategoryType } from "@/lib/types";

type CategoryWithOptionalType = Category & {
  type?: CategoryType | string | null;
};

type CategoryGroupKey = "income" | "expense" | "both";

const emptyForm: CategoryPayload = {
  name: "",
  type: "expense",
  status: "active",
};

const categoryTypeLabels: Record<CategoryType, string> = {
  expense: "Despesa",
  income: "Receita",
  both: "Ambas",
};

const categoryGroups: Array<{ key: CategoryGroupKey; title: string }> = [
  { key: "income", title: "Receitas" },
  { key: "expense", title: "Despesas" },
  { key: "both", title: "Ambas" },
];

function getCategoryGroupKey(category: CategoryWithOptionalType): CategoryGroupKey {
  const type = category.type?.toLowerCase();

  if (type === "income" || type === "receita" || type === "receitas") {
    return "income";
  }

  if (type === "expense" || type === "despesa" || type === "despesas") {
    return "expense";
  }

  return "both";
}

function getCategoryBadge(category: CategoryWithOptionalType) {
  const type = category.type as CategoryType | undefined;
  return type && type in categoryTypeLabels ? categoryTypeLabels[type] : "Padrão";
}

function getEditableType(category: CategoryWithOptionalType): CategoryType {
  return category.type === "expense" || category.type === "income" || category.type === "both" ? category.type : "both";
}

interface CategoryFormProps {
  form: CategoryPayload;
  isEditing: boolean;
  isSubmitting: boolean;
  onCancel: () => void;
  onChange: (payload: CategoryPayload) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function CountBadge({ count }: { count: number }) {
  return (
    <span className="rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-semibold text-stone-500">
      {count}
    </span>
  );
}

function CategoryForm({ form, isEditing, isSubmitting, onCancel, onChange, onSubmit }: CategoryFormProps) {
  return (
    <form className="rounded-md border border-stone-100 bg-stone-50 p-4" onSubmit={onSubmit}>
      <div className="flex items-center gap-2">
        {isEditing ? <Pencil className="h-5 w-5 text-mint" /> : <Plus className="h-5 w-5 text-mint" />}
        <h3 className="text-base font-semibold text-ink">{isEditing ? "Editar categoria" : "Nova categoria"}</h3>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_220px]">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Nome</span>
          <input
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, name: event.target.value })}
            placeholder="Ex: Mercado, Salário, Moradia"
            required
            value={form.name}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-stone-600">Tipo</span>
          <select
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
            disabled={isSubmitting}
            onChange={(event) => onChange({ ...form, type: event.target.value as CategoryType })}
            value={form.type}
          >
            <option value="expense">Despesa</option>
            <option value="income">Receita</option>
            <option value="both">Ambas</option>
          </select>
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <UiButton disabled={isSubmitting} icon={isEditing ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
          {isEditing ? "Salvar categoria" : "Criar categoria"}
        </UiButton>
        <UiButton disabled={isSubmitting} onClick={onCancel} variant="secondary">
          Cancelar
        </UiButton>
      </div>
    </form>
  );
}

export function SettingsCategoriesSection({ initialCategories }: { initialCategories: Category[] }) {
  const toast = useToast();
  const [categories, setCategories] = useState<Category[]>(initialCategories);
  const [form, setForm] = useState<CategoryPayload>({ ...emptyForm });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState<Category | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(initialCategories.length === 0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refetchCategories() {
    const nextCategories = await getCategories();
    setCategories(nextCategories);
  }

  useEffect(() => {
    if (initialCategories.length > 0) {
      return;
    }
    void Promise.resolve()
      .then(refetchCategories)
      .catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar categorias."))
      .finally(() => setIsLoading(false));
  }, [initialCategories.length]);

  function startCreate() {
    setMessage(null);
    setError(null);
    setEditingId(null);
    setConfirmingDelete(null);
    setForm({ ...emptyForm });
    setShowCreateForm(true);
  }

  function startEdit(category: CategoryWithOptionalType) {
    if (category.is_system) {
      return;
    }
    setMessage(null);
    setError(null);
    setShowCreateForm(false);
    setConfirmingDelete(null);
    setEditingId(category.id);
    setForm({
      name: category.name,
      type: getEditableType(category),
      status: "active",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm({ ...emptyForm });
    setShowCreateForm(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    setIsSubmitting(true);

    try {
      if (editingId) {
        await updateCategory(editingId, form);
        setMessage("Categoria atualizada.");
        toast.success("Categoria atualizada.");
      } else {
        await createCategory(form);
        setMessage("Categoria criada.");
        toast.success("Categoria criada.");
      }
      await refetchCategories();
      cancelEdit();
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Falha ao salvar categoria.";
      setError(messageText);
      toast.error(messageText);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function confirmDelete() {
    if (!confirmingDelete) {
      return;
    }

    setMessage(null);
    setError(null);
    setIsSubmitting(true);

    try {
      await deleteCategory(confirmingDelete.id);
      await refetchCategories();
      if (editingId === confirmingDelete.id) {
        cancelEdit();
      }
      setConfirmingDelete(null);
      setMessage("Categoria inativada.");
      toast.success("Categoria inativada.");
    } catch (err) {
      const messageText = err instanceof Error ? err.message : "Falha ao inativar categoria.";
      setError(messageText);
      toast.error(messageText);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
    <article id="settings-categories" className="scroll-mt-6 rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Tags className="h-5 w-5 text-mint" />
          <h2 className="text-lg font-semibold text-ink">Minhas categorias</h2>
        </div>
        <UiButton disabled={isSubmitting} icon={<Plus className="h-4 w-4" />} onClick={startCreate} variant="primary">
          Adicionar categoria
        </UiButton>
      </div>
      <p className="mt-4 text-sm leading-6 text-stone-600">
        Categorias disponíveis para organizar seus lançamentos financeiros.
      </p>

      {message ? <p className="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
      {error ? <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      {showCreateForm ? (
        <div className="mt-5">
          <CategoryForm
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
        <div className="mt-5 space-y-5" aria-busy="true" aria-live="polite">
          {categoryGroups.map((group) => (
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
      ) : (
      <div className="mt-5 space-y-5">
        {categoryGroups.map((group) => {
          const groupCategories = (categories as CategoryWithOptionalType[]).filter((category) => getCategoryGroupKey(category) === group.key);

          return (
            <section key={group.key} className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-ink">{group.title}</h3>
                <CountBadge count={groupCategories.length} />
              </div>
              <div className="space-y-2">
                {groupCategories.length === 0 ? (
                  <p className="rounded-md border border-stone-100 bg-stone-50 px-4 py-6 text-center text-sm text-stone-500">
                    Nenhuma categoria neste grupo.
                  </p>
                ) : null}

                {groupCategories.map((category) =>
                  editingId === category.id ? (
                    <CategoryForm
                      key={category.id}
                      form={form}
                      isEditing
                      isSubmitting={isSubmitting}
                      onCancel={cancelEdit}
                      onChange={setForm}
                      onSubmit={handleSubmit}
                    />
                  ) : (
                    <div key={category.id} className="flex items-center justify-between gap-3 rounded-md border border-stone-100 bg-stone-50 px-4 py-3">
                      <div className="min-w-0">
                        <span className="block truncate text-sm font-medium text-ink">{category.name}</span>
                        {category.is_system ? <span className="mt-1 block text-xs text-stone-500">Categoria padrão do sistema</span> : null}
                      </div>

                      <div className="flex shrink-0 items-center gap-2">
                        {category.is_system ? (
                          <span className="rounded-full border border-mint/30 bg-emerald-50 px-2 py-1 text-xs font-semibold text-mint">
                            Sistema
                          </span>
                        ) : null}
                        <span className="rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-medium text-stone-500">
                          {getCategoryBadge(category)}
                        </span>
                        {!category.is_system ? (
                          <>
                            <IconButton
                              aria-label={`Editar categoria ${category.name}`}
                              disabled={isSubmitting}
                              icon={<Pencil className="h-4 w-4" />}
                              onClick={() => startEdit(category)}
                              title="Editar"
                              variant="secondary"
                            />
                            <IconButton
                              aria-label={`Inativar categoria ${category.name}`}
                              disabled={isSubmitting}
                              icon={<Trash2 className="h-4 w-4" />}
                              onClick={() => {
                                setMessage(null);
                                setError(null);
                                setConfirmingDelete(category);
                              }}
                              title="Excluir"
                              variant="danger"
                            />
                          </>
                        ) : null}
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
    </article>
    {confirmingDelete ? (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4 py-6">
        <div className="w-full max-w-md rounded-lg border border-stone-200 bg-white p-5 shadow-xl">
          <h3 className="text-lg font-semibold text-ink">Inativar categoria?</h3>
          <div className="mt-3 space-y-2 text-sm leading-6 text-stone-600">
            <p>A categoria deixará de aparecer em:</p>
            <ul className="list-disc pl-5">
              <li>Transações</li>
              <li>Importações</li>
              <li>Regras</li>
            </ul>
            <p>Os lançamentos existentes serão preservados.</p>
          </div>
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <UiButton disabled={isSubmitting} onClick={() => setConfirmingDelete(null)} variant="secondary">
              Cancelar
            </UiButton>
            <UiButton disabled={isSubmitting} onClick={confirmDelete} variant="danger">
              Inativar categoria
            </UiButton>
          </div>
        </div>
      </div>
    ) : null}
    </>
  );
}
