"use client";

import { FormEvent, useState } from "react";
import { Pencil, Plus, Target, Trash2, WalletCards } from "lucide-react";
import { IconButton, UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import { createBudget, createFinancialGoal, deleteBudget, deleteFinancialGoal, getPlanningOverview, updateBudget, updateFinancialGoal } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getCategoryName } from "@/lib/labels";
import type { Budget, BudgetPayload, Category, FinancialGoal, FinancialGoalPayload, PlanningOverview } from "@/lib/types";

const currentMonth = new Date().toISOString().slice(0, 7);

const emptyGoal: FinancialGoalPayload = {
  name: "",
  target_amount: "0",
  current_amount: "0",
  target_date: null,
  status: "active",
  notes: null
};

const emptyBudget: BudgetPayload = {
  name: "",
  amount: "0",
  period_month: currentMonth,
  category_id: null,
  status: "active",
  notes: null
};

export function PlanningContent({ initialOverview, categories }: { initialOverview: PlanningOverview; categories: Category[] }) {
  const toast = useToast();
  const [overview, setOverview] = useState(initialOverview);
  const [goalForm, setGoalForm] = useState<FinancialGoalPayload>(emptyGoal);
  const [budgetForm, setBudgetForm] = useState<BudgetPayload>(emptyBudget);
  const [editingGoalId, setEditingGoalId] = useState<string | null>(null);
  const [editingBudgetId, setEditingBudgetId] = useState<string | null>(null);

  async function reload(periodMonth = budgetForm.period_month) {
    setOverview(await getPlanningOverview(periodMonth));
  }

  async function submitGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      if (editingGoalId) {
        await updateFinancialGoal(editingGoalId, goalForm);
        toast.success("Meta atualizada.");
      } else {
        await createFinancialGoal(goalForm);
        toast.success("Meta cadastrada.");
      }
      setGoalForm(emptyGoal);
      setEditingGoalId(null);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar meta.");
    }
  }

  async function submitBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      if (editingBudgetId) {
        await updateBudget(editingBudgetId, budgetForm);
        toast.success("Orçamento atualizado.");
      } else {
        await createBudget(budgetForm);
        toast.success("Orçamento cadastrado.");
      }
      setBudgetForm({ ...emptyBudget, period_month: budgetForm.period_month });
      setEditingBudgetId(null);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar orçamento.");
    }
  }

  function editGoal(goal: FinancialGoal) {
    setEditingGoalId(goal.id);
    setGoalForm({
      name: goal.name,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      target_date: goal.target_date,
      status: goal.status,
      notes: goal.notes
    });
  }

  function editBudget(budget: Budget) {
    setEditingBudgetId(budget.id);
    setBudgetForm({
      name: budget.name,
      amount: budget.amount,
      period_month: budget.period_month,
      category_id: budget.category_id,
      status: budget.status,
      notes: budget.notes
    });
  }

  async function removeGoal(goalId: string) {
    if (!window.confirm("Inativar esta meta?")) return;
    await deleteFinancialGoal(goalId);
    toast.danger("Meta inativada.");
    await reload();
  }

  async function removeBudget(budgetId: string) {
    if (!window.confirm("Inativar este orçamento?")) return;
    await deleteBudget(budgetId);
    toast.danger("Orçamento inativado.");
    await reload();
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">Planejamento</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Metas e Orçamentos</h1>
        <p className="mt-2 text-sm text-stone-500">Acompanhe objetivos financeiros e limites mensais de gasto em uma visão única.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-4 py-3">
            <h2 className="flex items-center gap-2 font-semibold text-ink"><Target className="h-4 w-4 text-mint" /> Metas</h2>
          </div>
          <form onSubmit={submitGoal} className="grid gap-3 border-b border-stone-100 p-4 md:grid-cols-2">
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Nome da meta" value={goalForm.name} onChange={(event) => setGoalForm({ ...goalForm, name: event.target.value })} required />
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Valor alvo" type="number" step="0.01" value={goalForm.target_amount} onChange={(event) => setGoalForm({ ...goalForm, target_amount: event.target.value })} required />
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Valor atual" type="number" step="0.01" value={goalForm.current_amount} onChange={(event) => setGoalForm({ ...goalForm, current_amount: event.target.value })} />
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" type="date" value={goalForm.target_date ?? ""} onChange={(event) => setGoalForm({ ...goalForm, target_date: event.target.value || null })} />
            <UiButton className="md:col-span-2" icon={<Plus className="h-4 w-4" />} type="submit" variant="primary">{editingGoalId ? "Salvar meta" : "Criar meta"}</UiButton>
          </form>
          <div className="divide-y divide-stone-100">
            {overview.goals.map((goal) => <GoalRow key={goal.id} goal={goal} onEdit={editGoal} onRemove={removeGoal} />)}
            {overview.goals.length === 0 ? <p className="px-4 py-8 text-center text-sm text-stone-500">Nenhuma meta cadastrada.</p> : null}
          </div>
        </section>

        <section className="rounded-lg border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-100 px-4 py-3">
            <h2 className="flex items-center gap-2 font-semibold text-ink"><WalletCards className="h-4 w-4 text-mint" /> Orçamentos</h2>
          </div>
          <form onSubmit={submitBudget} className="grid gap-3 border-b border-stone-100 p-4 md:grid-cols-2">
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Nome do orçamento" value={budgetForm.name} onChange={(event) => setBudgetForm({ ...budgetForm, name: event.target.value })} required />
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Limite mensal" type="number" step="0.01" value={budgetForm.amount} onChange={(event) => setBudgetForm({ ...budgetForm, amount: event.target.value })} required />
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" type="month" value={budgetForm.period_month} onChange={(event) => { const month = event.target.value || currentMonth; setBudgetForm({ ...budgetForm, period_month: month }); void reload(month); }} />
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={budgetForm.category_id ?? ""} onChange={(event) => setBudgetForm({ ...budgetForm, category_id: event.target.value || null })}>
              <option value="">Todas as categorias</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <UiButton className="md:col-span-2" icon={<Plus className="h-4 w-4" />} type="submit" variant="primary">{editingBudgetId ? "Salvar orçamento" : "Criar orçamento"}</UiButton>
          </form>
          <div className="divide-y divide-stone-100">
            {overview.budgets.map((budget) => <BudgetRow key={budget.id} budget={budget} categories={categories} onEdit={editBudget} onRemove={removeBudget} />)}
            {overview.budgets.length === 0 ? <p className="px-4 py-8 text-center text-sm text-stone-500">Nenhum orçamento para este mês.</p> : null}
          </div>
        </section>
      </div>
    </section>
  );
}

function GoalRow({ goal, onEdit, onRemove }: { goal: FinancialGoal; onEdit: (goal: FinancialGoal) => void; onRemove: (id: string) => void }) {
  return (
    <div className="space-y-3 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-ink">{goal.name}</p>
          <p className="text-sm text-stone-500">{formatCurrency(goal.current_amount)} de {formatCurrency(goal.target_amount)}</p>
        </div>
        <div className="flex gap-1.5">
          <IconButton aria-label="Editar meta" icon={<Pencil className="h-4 w-4" />} onClick={() => onEdit(goal)} title="Editar" variant="secondary" />
          <IconButton aria-label="Inativar meta" icon={<Trash2 className="h-4 w-4" />} onClick={() => onRemove(goal.id)} title="Inativar" variant="danger" />
        </div>
      </div>
      <Progress value={Number(goal.progress_percent)} />
      <p className="text-xs text-stone-500">Faltam {formatCurrency(goal.remaining_amount)}{goal.target_date ? ` ate ${goal.target_date}` : ""}.</p>
    </div>
  );
}

function BudgetRow({ budget, categories, onEdit, onRemove }: { budget: Budget; categories: Category[]; onEdit: (budget: Budget) => void; onRemove: (id: string) => void }) {
  const tone = budget.alert_level === "over_limit" ? "text-red-600" : budget.alert_level === "near_limit" ? "text-amber-600" : "text-stone-500";
  return (
    <div className="space-y-3 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-ink">{budget.name}</p>
          <p className="text-sm text-stone-500">{getCategoryName(budget.category_id, categories)} · {budget.period_month}</p>
        </div>
        <div className="flex gap-1.5">
          <IconButton aria-label="Editar orçamento" icon={<Pencil className="h-4 w-4" />} onClick={() => onEdit(budget)} title="Editar" variant="secondary" />
          <IconButton aria-label="Inativar orçamento" icon={<Trash2 className="h-4 w-4" />} onClick={() => onRemove(budget.id)} title="Inativar" variant="danger" />
        </div>
      </div>
      <Progress value={Number(budget.usage_percent)} />
      <p className={`text-xs ${tone}`}>{formatCurrency(budget.spent_amount)} usados de {formatCurrency(budget.amount)}. Saldo: {formatCurrency(budget.remaining_amount)}.</p>
    </div>
  );
}

function Progress({ value }: { value: number }) {
  const width = Math.max(0, Math.min(value, 100));
  return (
    <div className="h-2 overflow-hidden rounded-full bg-stone-100">
      <div className="h-full rounded-full bg-mint" style={{ width: `${width}%` }} />
    </div>
  );
}
