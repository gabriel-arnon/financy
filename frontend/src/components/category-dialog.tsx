"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Plus, Save, X } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createCategory } from "@/lib/api";
import type { Category, CategoryPayload, CategoryType } from "@/lib/types";

interface CategoryDialogProps {
  initialName?: string;
  initialType?: CategoryType;
  open: boolean;
  onClose: () => void;
  onCreated: (category: Category) => void;
}

const emptyCategory: CategoryPayload = {
  name: "",
  type: "expense",
  status: "active",
};

export function CategoryDialog({ initialName = "", initialType = "expense", open, onClose, onCreated }: CategoryDialogProps) {
  const toast = useToast();
  const firstFieldRef = useRef<HTMLInputElement | null>(null);
  const [form, setForm] = useState<CategoryPayload>({ ...emptyCategory, type: initialType });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const timeoutId = window.setTimeout(() => {
      setForm({ ...emptyCategory, name: initialName, type: initialType });
      setError(null);
      firstFieldRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [initialName, initialType, open]);

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
      const category = await createCategory({ ...form, name: form.name.trim() });
      toast.success(category.action === "reactivated" ? "Categoria reativada." : "Categoria criada.");
      onCreated(category);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao criar categoria.";
      setError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <button className="absolute inset-0 bg-black/30" type="button" aria-label="Fechar criacao de categoria" onClick={onClose} disabled={isSubmitting} />
      <section aria-labelledby="category-dialog-title" aria-modal="true" className="relative w-full max-w-lg rounded-lg border border-stone-200 bg-white p-5 shadow-2xl" role="dialog">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-mint">Categoria</p>
            <h2 id="category-dialog-title" className="mt-1 text-xl font-semibold text-ink">Adicionar categoria</h2>
          </div>
          <button className="rounded-md border border-stone-200 p-2 text-stone-600 transition hover:bg-stone-50" type="button" onClick={onClose} aria-label="Fechar" disabled={isSubmitting}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
          {error ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
          <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
            <label className="grid gap-1.5 text-sm font-medium text-stone-600">
              Nome
              <input
                ref={firstFieldRef}
                className="h-10 rounded-md border border-stone-200 px-3 text-sm text-ink outline-none focus:border-mint"
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Ex: Moradia"
                required
                value={form.name}
              />
            </label>
            <label className="grid gap-1.5 text-sm font-medium text-stone-600">
              Tipo
              <select className="h-10 rounded-md border border-stone-200 px-3 text-sm text-ink outline-none focus:border-mint" disabled={isSubmitting} onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as CategoryType }))} value={form.type}>
                <option value="expense">Despesa</option>
                <option value="income">Receita</option>
                <option value="both">Ambas</option>
              </select>
            </label>
          </div>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <UiButton disabled={isSubmitting} onClick={onClose} type="button" variant="ghost">
              Cancelar
            </UiButton>
            <UiButton disabled={isSubmitting || !form.name.trim()} icon={isSubmitting ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />} type="submit" variant="primary">
              {isSubmitting ? "Salvando..." : "Adicionar categoria"}
            </UiButton>
          </div>
        </form>
      </section>
    </div>
  );
}
