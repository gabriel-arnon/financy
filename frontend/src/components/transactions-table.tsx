"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpDown, Pencil, Plus, Save, Search, Trash2, Wand2, X } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { createClassificationRule, createTransaction, deleteTransaction, updateTransaction } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { formatAccountName, formatCardName, formatCardWithAccount, getAccountName, getCardNameWithAccount, getCategoryName, isActiveEntity, translateTransactionType } from "@/lib/labels";
import type { Account, Card, Category, Transaction, TransactionPayload, TransactionType } from "@/lib/types";

interface TransactionsTableProps {
  transactions: Transaction[];
  categories: Category[];
  accounts: Account[];
  cards: Card[];
  initialCardId?: string | null;
  initialCardStatementId?: string | null;
}

type SortKey = "date" | "amount" | "description";
type SortDirection = "asc" | "desc";
type AsyncAction = "save" | "rule" | "delete" | "bulk-category" | "bulk-rule" | "bulk-delete" | "create" | null;

interface ManualTransactionForm {
  transaction_date: string;
  description: string;
  amount: string;
  type: TransactionType;
  category_id: string;
  account_id: string;
  card_id: string;
  status: string;
}

interface ConfirmDialogState {
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => Promise<void>;
}

const transactionTypes: Array<TransactionType | "all"> = ["all", "expense", "income", "transfer", "payment", "refund"];
const manualTransactionTypes: TransactionType[] = ["expense", "income", "transfer", "payment", "refund"];
const transactionStatuses = ["pending", "confirmed", "reconciled", "ignored"];
const uncategorizedValue = "__none__";
const ignoredWords = new Set(["PARC", "COMPRA", "PAGAMENTO", "PGTO", "BR", "SAO"]);
const incomeTypes = new Set<TransactionType>(["income", "refund"]);
const expenseTypes = new Set<TransactionType>(["expense", "payment"]);
const pageSize = 25;

function firstRelevantKeyword(description: string) {
  return description
    .toUpperCase()
    .replace(/[^A-Z0-9\s]/g, " ")
    .split(/\s+/)
    .find((word) => word.length >= 3 && !ignoredWords.has(word)) ?? "";
}

function transactionAmountPresentation(transaction: Transaction) {
  const amount = Math.abs(Number(transaction.amount));
  const isIncome = incomeTypes.has(transaction.type);
  const isExpense = expenseTypes.has(transaction.type);

  return {
    value: Number.isFinite(amount) ? amount : 0,
    prefix: isIncome ? "+" : isExpense ? "-" : "",
    className: isIncome ? "text-mint" : isExpense ? "text-coral" : "text-ink"
  };
}

function isTransactionUncategorized(transaction: Transaction, categoryIds: Set<string>) {
  return !transaction.category_id || !categoryIds.has(transaction.category_id);
}

function defaultManualForm(): ManualTransactionForm {
  return {
    transaction_date: new Date().toISOString().slice(0, 10),
    description: "",
    amount: "",
    type: "expense",
    category_id: "",
    account_id: "",
    card_id: "",
    status: "confirmed"
  };
}

function useDebouncedValue<T>(value: T, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debouncedValue;
}

export function TransactionsTable({ transactions, categories, accounts, cards, initialCardId = null, initialCardStatementId = null }: TransactionsTableProps) {
  const router = useRouter();
  const [rows, setRows] = useState(transactions);
  const [query, setQuery] = useState("");
  const [type, setType] = useState<TransactionType | "all">("all");
  const [category, setCategory] = useState("all");
  const [account, setAccount] = useState("all");
  const [card, setCard] = useState(initialCardId ?? "all");
  const [status, setStatus] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);
  const [drawerTransactionId, setDrawerTransactionId] = useState<string | null>(null);
  const [draftDescription, setDraftDescription] = useState("");
  const [draftCategoryId, setDraftCategoryId] = useState("");
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState("");
  const [asyncAction, setAsyncAction] = useState<AsyncAction>(null);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<"success" | "error">("success");
  const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);
  const [manualForm, setManualForm] = useState<ManualTransactionForm>(() => defaultManualForm());
  const lastFocusedElementRef = useRef<HTMLElement | null>(null);
  const detailDescriptionRef = useRef<HTMLInputElement | null>(null);
  const createDateRef = useRef<HTMLInputElement | null>(null);
  const confirmCancelRef = useRef<HTMLButtonElement | null>(null);
  const debouncedQuery = useDebouncedValue(query, 250);

  const categoryIds = useMemo(() => new Set(categories.map((item) => item.id)), [categories]);
  const activeAccounts = useMemo(() => accounts.filter(isActiveEntity), [accounts]);
  const activeCards = useMemo(() => cards.filter(isActiveEntity), [cards]);
  const cardAccountById = useMemo(() => new Map(cards.map((item) => [item.id, item.account_id])), [cards]);
  const initialCard = useMemo(() => cards.find((item) => item.id === initialCardId), [cards, initialCardId]);
  const statuses = useMemo(() => Array.from(new Set(rows.map((transaction) => transaction.status).filter(Boolean))).sort(), [rows]);
  const drawerTransaction = useMemo(() => rows.find((transaction) => transaction.id === drawerTransactionId) ?? null, [drawerTransactionId, rows]);
  const isBusy = asyncAction !== null;

  function rememberFocusedElement() {
    lastFocusedElementRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  }

  const restorePreviousFocus = useCallback(function restorePreviousFocus() {
    window.setTimeout(() => lastFocusedElementRef.current?.focus(), 0);
  }, []);

  function updateRow(transactionId: string, patch: Partial<Transaction>) {
    setRows((current) => current.map((item) => (item.id === transactionId ? { ...item, ...patch } : item)));
  }

  function showMessage(typeValue: "success" | "error", text: string) {
    setMessageType(typeValue);
    setMessage(text);
  }

  function resetVisibleList() {
    setVisibleCount(pageSize);
  }

  const filtered = useMemo(() => {
    const normalizedQuery = debouncedQuery.trim().toLowerCase();
    return rows.filter((transaction) => {
      const matchesQuery = !normalizedQuery || transaction.description.toLowerCase().includes(normalizedQuery);
      const matchesType = type === "all" || transaction.type === type;
      const isUncategorized = isTransactionUncategorized(transaction, categoryIds);
      const matchesCategory =
        category === "all" ||
        (category === uncategorizedValue && isUncategorized) ||
        transaction.category_id === category;
      const matchesAccount =
        account === "all" ||
        transaction.account_id === account ||
        (transaction.card_id ? cardAccountById.get(transaction.card_id) === account : false);
      const matchesCard = card === "all" || transaction.card_id === card;
      const matchesStatus = status === "all" || transaction.status === status;
      const matchesStart = !startDate || transaction.transaction_date >= startDate;
      const matchesEnd = !endDate || transaction.transaction_date <= endDate;
      const matchesStatement = !initialCardStatementId || transaction.card_statement_id === initialCardStatementId;
      return matchesQuery && matchesType && matchesCategory && matchesAccount && matchesCard && matchesStatus && matchesStart && matchesEnd && matchesStatement;
    });
  }, [account, card, cardAccountById, category, categoryIds, debouncedQuery, endDate, initialCardStatementId, rows, startDate, status, type]);

  const summary = useMemo(() => {
    const income = filtered
      .filter((transaction) => incomeTypes.has(transaction.type))
      .reduce((total, transaction) => total + Math.abs(Number(transaction.amount)), 0);
    const expenses = filtered
      .filter((transaction) => expenseTypes.has(transaction.type))
      .reduce((total, transaction) => total + Math.abs(Number(transaction.amount)), 0);

    return {
      total: filtered.length,
      income,
      expenses,
      result: income - expenses
    };
  }, [filtered]);

  const sortedTransactions = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let comparison = 0;
      if (sortKey === "date") {
        comparison = a.transaction_date.localeCompare(b.transaction_date);
      } else if (sortKey === "amount") {
        comparison = Number(a.amount) - Number(b.amount);
      } else {
        comparison = a.description.localeCompare(b.description, "pt-BR", { sensitivity: "base" });
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [filtered, sortDirection, sortKey]);

  const visibleTransactions = useMemo(() => sortedTransactions.slice(0, visibleCount), [sortedTransactions, visibleCount]);
  const uncategorizedCount = useMemo(() => filtered.filter((transaction) => isTransactionUncategorized(transaction, categoryIds)).length, [categoryIds, filtered]);
  const selectedTransactions = useMemo(() => rows.filter((transaction) => selectedIds.has(transaction.id)), [rows, selectedIds]);
  const selectedCount = selectedIds.size;
  const visibleIds = useMemo(() => visibleTransactions.map((transaction) => transaction.id), [visibleTransactions]);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
  const hasMoreTransactions = visibleCount < sortedTransactions.length;

  function changeSort(nextKey: SortKey) {
    setSortDirection((currentDirection) => (sortKey === nextKey && currentDirection === "asc" ? "desc" : "asc"));
    setSortKey(nextKey);
    resetVisibleList();
  }

  function resetFilters() {
    setQuery("");
    setType("all");
    setCategory("all");
    setAccount("all");
    setCard(initialCardId ?? "all");
    setStatus("all");
    setStartDate("");
    setEndDate("");
    resetVisibleList();
  }

  function filterUncategorizedTransactions() {
    setCategory(uncategorizedValue);
    resetVisibleList();
  }

  function openDrawer(transaction: Transaction) {
    rememberFocusedElement();
    setSelectedTransactionId(transaction.id);
    setDrawerTransactionId(transaction.id);
    setDraftDescription(transaction.description);
    setDraftCategoryId(transaction.category_id ?? "");
  }

  const closeDrawer = useCallback(function closeDrawer(restoreFocus = true) {
    setDrawerTransactionId(null);
    if (restoreFocus) restorePreviousFocus();
  }, [restorePreviousFocus]);

  function openCreateDrawer() {
    rememberFocusedElement();
    setDrawerTransactionId(null);
    setSelectedTransactionId(null);
    setIsCreateDrawerOpen(true);
    setMessage(null);
  }

  const closeCreateDrawer = useCallback(function closeCreateDrawer(restoreFocus = true) {
    setIsCreateDrawerOpen(false);
    if (restoreFocus) restorePreviousFocus();
  }, [restorePreviousFocus]);

  const closeConfirmDialog = useCallback(function closeConfirmDialog(restoreFocus = true) {
    setConfirmDialog(null);
    if (restoreFocus) restorePreviousFocus();
  }, [restorePreviousFocus]);

  useEffect(() => {
    if (drawerTransaction) {
      detailDescriptionRef.current?.focus();
    }
  }, [drawerTransaction]);

  useEffect(() => {
    if (isCreateDrawerOpen) {
      createDateRef.current?.focus();
    }
  }, [isCreateDrawerOpen]);

  useEffect(() => {
    if (confirmDialog) {
      confirmCancelRef.current?.focus();
    }
  }, [confirmDialog]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (confirmDialog) {
        closeConfirmDialog();
        return;
      }
      if (isCreateDrawerOpen) {
        closeCreateDrawer();
        return;
      }
      if (drawerTransaction) {
        closeDrawer();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeConfirmDialog, closeCreateDrawer, closeDrawer, confirmDialog, drawerTransaction, isCreateDrawerOpen]);

  function updateManualForm(patch: Partial<ManualTransactionForm>) {
    setManualForm((current) => ({ ...current, ...patch }));
  }

  function drawerDraftTransaction(transaction: Transaction): Transaction {
    return {
      ...transaction,
      description: draftDescription,
      category_id: draftCategoryId || null
    };
  }

  function toggleSelected(transactionId: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(transactionId)) {
        next.delete(transactionId);
      } else {
        next.add(transactionId);
      }
      return next;
    });
  }

  function toggleCurrentPageSelection() {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (allVisibleSelected) {
        visibleIds.forEach((id) => next.delete(id));
      } else {
        visibleIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  async function runAsync(action: Exclude<AsyncAction, null>, callback: () => Promise<void>) {
    setAsyncAction(action);
    try {
      await callback();
    } catch (err) {
      showMessage("error", err instanceof Error ? err.message : "Falha ao executar ação.");
    } finally {
      setAsyncAction(null);
    }
  }

  async function createManualTransaction() {
    await runAsync("create", async () => {
      const description = manualForm.description.trim();
      const amount = Number(manualForm.amount.replace(",", "."));

      if (!manualForm.transaction_date || !description || !manualForm.amount.trim()) {
        showMessage("error", "Informe data, descrição e valor para criar a transação.");
        return;
      }

      if (!Number.isFinite(amount) || amount <= 0) {
        showMessage("error", "Informe um valor válido maior que zero.");
        return;
      }

      const payload: TransactionPayload = {
        transaction_date: manualForm.transaction_date,
        description,
        original_description: description,
        amount: amount.toFixed(2),
        type: manualForm.type,
        category_id: manualForm.category_id || null,
        account_id: manualForm.account_id || null,
        card_id: manualForm.card_id || null,
        card_statement_id: null,
        source_file_id: null,
        installment_current: null,
        installment_total: null,
        status: manualForm.status
      };

      const created = await createTransaction(payload);
      setRows((current) => [created, ...current]);
      setManualForm(defaultManualForm());
      closeCreateDrawer(false);
      setSelectedTransactionId(created.id);
      setDrawerTransactionId(created.id);
      setDraftDescription(created.description);
      setDraftCategoryId(created.category_id ?? "");
      resetVisibleList();
      showMessage("success", "Transação criada.");
      router.refresh();
    });
  }

  async function saveRow(transaction: Transaction) {
    await runAsync("save", async () => {
      const saved = await updateTransaction(transaction.id, {
        description: transaction.description,
        category_id: transaction.category_id,
        type: transaction.type
      });
      updateRow(transaction.id, saved);
      setDraftDescription(saved.description);
      setDraftCategoryId(saved.category_id ?? "");
      showMessage("success", "Transação atualizada.");
    });
  }

  async function createRuleFromRow(transaction: Transaction) {
    await runAsync("rule", async () => {
      if (!transaction.category_id) {
        showMessage("error", "Escolha uma categoria antes de criar a regra.");
        return;
      }
      const keyword = firstRelevantKeyword(transaction.description);
      if (!keyword) {
        showMessage("error", "Não encontrei uma palavra relevante para criar a regra.");
        return;
      }
      await createClassificationRule({
        keyword,
        category_id: transaction.category_id,
        transaction_type: transaction.type,
        priority: 100,
        status: "active",
        match_scope: "both",
        auto_created: true
      });
      showMessage("success", `Regra criada para ${keyword}.`);
    });
  }

  async function deleteRowConfirmed(transaction: Transaction) {
    await runAsync("delete", async () => {
      await deleteTransaction(transaction.id);
      setRows((current) => current.filter((item) => item.id !== transaction.id));
      setSelectedIds((current) => {
        const next = new Set(current);
        next.delete(transaction.id);
        return next;
      });
      setSelectedTransactionId((current) => (current === transaction.id ? null : current));
      setDrawerTransactionId((current) => (current === transaction.id ? null : current));
      showMessage("success", "Transação excluída.");
      router.refresh();
    });
  }

  function requestDeleteRow(transaction: Transaction) {
    rememberFocusedElement();
    setConfirmDialog({
      title: "Excluir transação",
      description: `Tem certeza que deseja excluir "${transaction.description}"? Esta ação não pode ser desfeita.`,
      confirmLabel: "Excluir transação",
      onConfirm: () => deleteRowConfirmed(transaction)
    });
  }

  async function applyBulkCategory() {
    await runAsync("bulk-category", async () => {
      if (selectedTransactions.length === 0) {
        showMessage("error", "Selecione ao menos uma transação.");
        return;
      }
      if (!bulkCategoryId) {
        showMessage("error", "Escolha uma categoria para aplicar em lote.");
        return;
      }
      const saved = await Promise.all(
        selectedTransactions.map((transaction) =>
          updateTransaction(transaction.id, {
            description: transaction.description,
            category_id: bulkCategoryId,
            type: transaction.type
          })
        )
      );
      setRows((current) => current.map((transaction) => saved.find((item) => item.id === transaction.id) ?? transaction));
      showMessage("success", `Categoria alterada em ${saved.length} transações.`);
    });
  }

  async function createBulkRules() {
    await runAsync("bulk-rule", async () => {
      const rulePayloads = selectedTransactions
        .map((transaction) => ({ transaction, keyword: firstRelevantKeyword(transaction.description) }))
        .filter(({ transaction, keyword }) => transaction.category_id && keyword);

      if (rulePayloads.length === 0) {
        showMessage("error", "Selecione transações categorizadas com descrições válidas para criar regras.");
        return;
      }

      await Promise.all(
        rulePayloads.map(({ transaction, keyword }) =>
          createClassificationRule({
            keyword,
            category_id: transaction.category_id ?? "",
            transaction_type: transaction.type,
            priority: 100,
            status: "active",
            match_scope: "both",
            auto_created: true
          })
        )
      );
      showMessage("success", `${rulePayloads.length} regras criadas.`);
    });
  }

  async function deleteSelectedConfirmed() {
    await runAsync("bulk-delete", async () => {
      const idsToDelete = new Set(selectedIds);
      await Promise.all(Array.from(idsToDelete).map((transactionId) => deleteTransaction(transactionId)));
      setRows((current) => current.filter((transaction) => !idsToDelete.has(transaction.id)));
      setSelectedIds(new Set());
      setSelectedTransactionId((current) => (current && idsToDelete.has(current) ? null : current));
      setDrawerTransactionId((current) => (current && idsToDelete.has(current) ? null : current));
      showMessage("success", `${idsToDelete.size} transações excluídas.`);
      router.refresh();
    });
  }

  function requestDeleteSelected() {
    if (selectedCount === 0) {
      showMessage("error", "Selecione ao menos uma transação.");
      return;
    }
    rememberFocusedElement();
    setConfirmDialog({
      title: "Excluir transações selecionadas",
      description: `Tem certeza que deseja excluir ${selectedCount} transações? Esta ação não pode ser desfeita.`,
      confirmLabel: "Excluir selecionadas",
      onConfirm: deleteSelectedConfirmed
    });
  }

  async function confirmCurrentDialog() {
    if (!confirmDialog) return;
    await confirmDialog.onConfirm();
    closeConfirmDialog(false);
  }

  const drawerAmount = drawerTransaction ? transactionAmountPresentation(drawerTransaction) : null;

  return (
    <div className="space-y-4">
      {message ? (
        <p
          aria-live="polite"
          className={`rounded-md px-3 py-2 text-sm ${messageType === "error" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}
          role={messageType === "error" ? "alert" : "status"}
        >
          {message}
        </p>
      ) : null}
      {initialCardStatementId ? (
        <p className="rounded-md border border-mint/20 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Exibindo apenas transações vinculadas à fatura selecionada.
        </p>
      ) : null}
      {initialCardId ? (
        <p className="rounded-md border border-mint/20 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Filtro ativo: {initialCard ? formatCardName(initialCard) : "Cartão não encontrado"}
        </p>
      ) : null}

      <div className="flex justify-end">
        <UiButton className="w-full sm:w-auto" icon={<Plus className="h-4 w-4" />} onClick={openCreateDrawer} variant="primary" disabled={isBusy}>
          Nova transação
        </UiButton>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Total transações</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{summary.total}</p>
          <p className="mt-3 text-xs text-stone-500">Lançamentos filtrados</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Entradas</p>
          <p className="mt-2 text-2xl font-semibold text-mint">{formatCurrency(summary.income)}</p>
          <p className="mt-3 text-xs text-stone-500">Receitas e estornos</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Saídas</p>
          <p className="mt-2 text-2xl font-semibold text-coral">{formatCurrency(summary.expenses)}</p>
          <p className="mt-3 text-xs text-stone-500">Despesas e pagamentos</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-500">Resultado</p>
          <p className={`mt-2 text-2xl font-semibold ${summary.result >= 0 ? "text-mint" : "text-coral"}`}>{formatCurrency(summary.result)}</p>
          <p className="mt-3 text-xs text-stone-500">Entradas menos saídas</p>
        </div>
      </div>

      <button
        aria-pressed={category === uncategorizedValue}
        className={`w-full rounded-lg border p-4 text-left shadow-sm transition focus:outline-none focus:ring-2 focus:ring-mint/60 ${
          category === uncategorizedValue ? "border-amber-300 bg-amber-50" : "border-amber-200 bg-white hover:bg-amber-50/70"
        }`}
        type="button"
        onClick={filterUncategorizedTransactions}
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-amber-900">Transações sem categoria</p>
            <p className="mt-1 text-sm text-stone-600">Use este atalho para revisar lançamentos que ainda precisam de classificação.</p>
          </div>
          <span className="inline-flex w-fit items-center rounded-md bg-amber-100 px-3 py-1.5 text-sm font-semibold text-amber-900">
            {uncategorizedCount} {uncategorizedCount === 1 ? "transação" : "transações"}
          </span>
        </div>
      </button>

      <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Filtros</h2>
            <p className="mt-1 text-xs text-stone-500">Refine a lista sem alterar os lançamentos.</p>
          </div>
          <button className="rounded-md border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50" type="button" onClick={resetFilters}>
            Limpar filtros
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Busca
            <span className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                className="h-10 w-full rounded-md border border-stone-200 pl-9 pr-3 text-sm font-normal text-ink outline-none focus:border-mint"
                placeholder="Buscar descrição"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  resetVisibleList();
                }}
              />
            </span>
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Data inicial
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); resetVisibleList(); }} />
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Data final
            <input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); resetVisibleList(); }} />
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Tipo
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={type} onChange={(event) => { setType(event.target.value as TransactionType | "all"); resetVisibleList(); }}>
              {transactionTypes.map((item) => (
                <option key={item} value={item}>{item === "all" ? "Todos os tipos" : translateTransactionType(item)}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Categoria
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={category} onChange={(event) => { setCategory(event.target.value); resetVisibleList(); }}>
              <option value="all">Todas categorias</option>
              <option value={uncategorizedValue}>Sem categoria</option>
              {categories.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Conta
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={account} onChange={(event) => { setAccount(event.target.value); resetVisibleList(); }}>
              <option value="all">Todas contas</option>
              {activeAccounts.map((item) => <option key={item.id} value={item.id}>{formatAccountName(item)}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Cartão
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={card} onChange={(event) => { setCard(event.target.value); resetVisibleList(); }}>
              <option value="all">Todos cartões</option>
              {activeCards.map((item) => <option key={item.id} value={item.id}>{formatCardWithAccount(item, accounts)}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-xs font-medium text-stone-500">
            Status
            <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={status} onChange={(event) => { setStatus(event.target.value); resetVisibleList(); }}>
              <option value="all">Todos status</option>
              {statuses.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Ações em lote</h2>
            <p className="mt-1 text-xs text-stone-500">{selectedCount} transações selecionadas</p>
          </div>
          <UiButton onClick={() => setSelectedIds(new Set())} size="sm" variant="ghost" disabled={selectedCount === 0 || isBusy}>
            Limpar seleção
          </UiButton>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
          <select className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={bulkCategoryId} onChange={(event) => setBulkCategoryId(event.target.value)} disabled={isBusy}>
            <option value="">Escolher categoria</option>
            {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <UiButton onClick={() => { void applyBulkCategory(); }} variant="secondary" disabled={selectedCount === 0 || !bulkCategoryId || isBusy}>
            {asyncAction === "bulk-category" ? "Aplicando..." : "Alterar categoria"}
          </UiButton>
          <UiButton icon={<Wand2 className="h-4 w-4" />} onClick={() => { void createBulkRules(); }} variant="secondary" disabled={selectedCount === 0 || isBusy}>
            {asyncAction === "bulk-rule" ? "Criando..." : "Criar regras"}
          </UiButton>
          <UiButton icon={<Trash2 className="h-4 w-4" />} onClick={requestDeleteSelected} variant="danger" disabled={selectedCount === 0 || isBusy}>
            Excluir selecionadas
          </UiButton>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-[62rem] divide-y divide-stone-200 text-sm">
            <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
              <tr>
                <th className="px-4 py-3">
                  <input aria-label="Selecionar página atual" className="h-4 w-4 rounded border-stone-300" type="checkbox" checked={allVisibleSelected} onChange={toggleCurrentPageSelection} />
                </th>
                <th className="px-4 py-3">
                  <button className="inline-flex items-center gap-1 font-semibold uppercase" type="button" onClick={() => changeSort("date")}>
                    Data
                    <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button className="inline-flex items-center gap-1 font-semibold uppercase" type="button" onClick={() => changeSort("description")}>
                    Descrição
                    <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </th>
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3">Origem</th>
                <th className="px-4 py-3 text-right">
                  <button className="inline-flex items-center justify-end gap-1 font-semibold uppercase" type="button" onClick={() => changeSort("amount")}>
                    Valor
                    <ArrowUpDown className="h-3.5 w-3.5" />
                  </button>
                </th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {visibleTransactions.map((transaction) => {
                const isSelected = selectedTransactionId === transaction.id;
                const isUncategorized = isTransactionUncategorized(transaction, categoryIds);
                const amount = transactionAmountPresentation(transaction);

                return (
                  <tr
                    key={transaction.id}
                    aria-current={isSelected ? "true" : undefined}
                    className={`cursor-pointer transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-mint/60 ${isUncategorized ? "bg-amber-50/60" : ""} ${isSelected ? "bg-emerald-50/70 ring-1 ring-inset ring-mint/30" : ""}`}
                    onClick={() => openDrawer(transaction)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        openDrawer(transaction);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <td className="px-4 py-3" onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()}>
                      <input aria-label={`Selecionar ${transaction.description}`} className="h-4 w-4 rounded border-stone-300" type="checkbox" checked={selectedIds.has(transaction.id)} onChange={() => toggleSelected(transaction.id)} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-stone-600">
                      <p>{formatDate(transaction.transaction_date)}</p>
                      <p className="mt-1 text-xs text-stone-400">{transaction.status}</p>
                    </td>
                    <td className="min-w-[28rem] px-4 py-3">
                      <p className="font-medium text-ink">{transaction.description}</p>
                      {transaction.original_description && transaction.original_description !== transaction.description ? (
                        <p className="mt-1 text-xs text-stone-400">{transaction.original_description}</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {isUncategorized ? (
                        <span className="inline-flex items-center rounded-md border border-amber-200 bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900">
                          Sem categoria
                        </span>
                      ) : (
                        getCategoryName(transaction.category_id, categories)
                      )}
                    </td>
                    <td className="min-w-56 px-4 py-3 text-stone-600">
                      {transaction.card_id ? `Cartão: ${getCardNameWithAccount(transaction.card_id, cards, accounts)}` : transaction.account_id ? `Conta: ${getAccountName(transaction.account_id, accounts)}` : "Sem origem"}
                      <p className="mt-1 text-xs text-stone-400">{translateTransactionType(transaction.type)}</p>
                    </td>
                    <td className={`px-4 py-3 text-right font-semibold ${amount.className}`}>{amount.prefix}{formatCurrency(amount.value)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2" onKeyDown={(event) => event.stopPropagation()}>
                        <UiButton
                          aria-label="Editar transação"
                          className="h-9 w-9 px-0 md:opacity-70 md:hover:opacity-100"
                          icon={<Pencil className="h-4 w-4" />}
                          onClick={(event) => {
                            event.stopPropagation();
                            openDrawer(transaction);
                          }}
                          size="sm"
                          title="Editar"
                          variant="secondary"
                        />
                        <UiButton
                          aria-label="Excluir transação"
                          className="h-9 w-9 px-0 md:opacity-70 md:hover:opacity-100"
                          icon={<Trash2 className="h-4 w-4" />}
                          onClick={(event) => {
                            event.stopPropagation();
                            requestDeleteRow(transaction);
                          }}
                          size="sm"
                          title="Excluir"
                          variant="danger"
                          disabled={isBusy}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-stone-500" colSpan={7}>Nenhuma transação encontrada.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {filtered.length > 0 ? (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-stone-100 px-4 py-4 sm:flex-row">
            <p className="text-sm text-stone-500">
              Exibindo {Math.min(visibleCount, filtered.length)} de {filtered.length} transações filtradas.
            </p>
            {hasMoreTransactions ? (
              <UiButton onClick={() => setVisibleCount((current) => current + pageSize)} variant="secondary">
                Carregar mais
              </UiButton>
            ) : (
              <p className="text-sm font-medium text-stone-600">Todas as transações foram carregadas.</p>
            )}
          </div>
        ) : null}
      </div>

      {isCreateDrawerOpen ? (
        <div className="fixed inset-0 z-40">
          <button className="absolute inset-0 hidden bg-black/30 md:block" type="button" aria-label="Fechar criação" onClick={() => closeCreateDrawer()} />
          <aside aria-labelledby="create-transaction-title" aria-modal="true" className="absolute inset-0 flex flex-col bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:w-[30rem]" role="dialog">
            <div className="flex items-start justify-between gap-4 border-b border-stone-200 px-5 py-4">
              <div>
                <p className="text-sm font-medium text-mint">Nova transação</p>
                <h2 id="create-transaction-title" className="mt-1 text-xl font-semibold text-ink">Criar lançamento manual</h2>
              </div>
              <button className="rounded-md border border-stone-200 p-2 text-stone-600 transition hover:bg-stone-50" type="button" onClick={() => closeCreateDrawer()} aria-label="Fechar" disabled={isBusy}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5">
              <div className="grid gap-4">
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Data
                  <input ref={createDateRef} className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" type="date" value={manualForm.transaction_date} onChange={(event) => updateManualForm({ transaction_date: event.target.value })} disabled={isBusy} />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Descrição
                  <input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={manualForm.description} onChange={(event) => updateManualForm({ description: event.target.value })} disabled={isBusy} />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Tipo
                  <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={manualForm.type} onChange={(event) => updateManualForm({ type: event.target.value as TransactionType })} disabled={isBusy}>
                    {manualTransactionTypes.map((item) => (
                      <option key={item} value={item}>{translateTransactionType(item)}</option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Categoria
                  <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={manualForm.category_id} onChange={(event) => updateManualForm({ category_id: event.target.value })} disabled={isBusy}>
                    <option value="">Sem categoria</option>
                    {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Conta
                  <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={manualForm.account_id} onChange={(event) => updateManualForm({ account_id: event.target.value, card_id: "" })} disabled={isBusy}>
                    <option value="">Sem conta</option>
                    {activeAccounts.map((item) => <option key={item.id} value={item.id}>{formatAccountName(item)}</option>)}
                  </select>
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Cartão
                  <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={manualForm.card_id} onChange={(event) => updateManualForm({ card_id: event.target.value, account_id: "" })} disabled={isBusy}>
                    <option value="">Sem cartão</option>
                    {activeCards.map((item) => <option key={item.id} value={item.id}>{formatCardWithAccount(item, accounts)}</option>)}
                  </select>
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Valor
                  <input className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" inputMode="decimal" placeholder="0,00" value={manualForm.amount} onChange={(event) => updateManualForm({ amount: event.target.value })} disabled={isBusy} />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Status
                  <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={manualForm.status} onChange={(event) => updateManualForm({ status: event.target.value })} disabled={isBusy}>
                    {transactionStatuses.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
              </div>
            </div>

            <div className="space-y-3 border-t border-stone-200 bg-white px-5 py-4">
              <UiButton className="w-full" icon={<Plus className="h-4 w-4" />} onClick={() => { void createManualTransaction(); }} variant="primary" disabled={isBusy}>
                {asyncAction === "create" ? "Criando..." : "Criar transação"}
              </UiButton>
              <UiButton className="w-full" icon={<X className="h-4 w-4" />} onClick={() => closeCreateDrawer()} variant="ghost" disabled={isBusy}>
                Fechar
              </UiButton>
            </div>
          </aside>
        </div>
      ) : null}

      {drawerTransaction && drawerAmount ? (
        <div className="fixed inset-0 z-40">
          <button className="absolute inset-0 hidden bg-black/30 md:block" type="button" aria-label="Fechar painel" onClick={() => closeDrawer()} />
          <aside aria-labelledby="transaction-detail-title" aria-modal="true" className="absolute inset-0 flex flex-col bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:w-[30rem]" role="dialog">
            <div className="flex items-start justify-between gap-4 border-b border-stone-200 px-5 py-4">
              <div>
                <p className="text-sm font-medium text-mint">Transação</p>
                <h2 id="transaction-detail-title" className="mt-1 text-xl font-semibold text-ink">Detalhes do lançamento</h2>
              </div>
              <button className="rounded-md border border-stone-200 p-2 text-stone-600 transition hover:bg-stone-50" type="button" onClick={() => closeDrawer()} aria-label="Fechar" disabled={isBusy}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5">
              <div className="grid gap-4">
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Data
                  <input className="h-10 rounded-md border border-stone-200 bg-stone-50 px-3 text-sm font-normal text-stone-600" value={formatDate(drawerTransaction.transaction_date)} readOnly />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Descrição
                  <input
                    ref={detailDescriptionRef}
                    className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint"
                    value={draftDescription}
                    onChange={(event) => setDraftDescription(event.target.value)}
                    disabled={isBusy}
                  />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Tipo
                  <input className="h-10 rounded-md border border-stone-200 bg-stone-50 px-3 text-sm font-normal text-stone-600" value={translateTransactionType(drawerTransaction.type)} readOnly />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Categoria
                  <select className="h-10 rounded-md border border-stone-200 px-3 text-sm font-normal text-ink outline-none focus:border-mint" value={draftCategoryId} onChange={(event) => setDraftCategoryId(event.target.value)} disabled={isBusy}>
                    <option value="">Sem categoria</option>
                    {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Conta
                  <input className="h-10 rounded-md border border-stone-200 bg-stone-50 px-3 text-sm font-normal text-stone-600" value={getAccountName(drawerTransaction.account_id, accounts)} readOnly />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Cartão
                  <input className="h-10 rounded-md border border-stone-200 bg-stone-50 px-3 text-sm font-normal text-stone-600" value={getCardNameWithAccount(drawerTransaction.card_id, cards, accounts)} readOnly />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Valor
                  <input className="h-10 rounded-md border border-stone-200 bg-stone-50 px-3 text-sm font-normal text-stone-600" value={`${drawerAmount.prefix}${formatCurrency(drawerAmount.value)}`} readOnly />
                </label>
                <label className="grid gap-1.5 text-xs font-medium text-stone-500">
                  Status
                  <input className="h-10 rounded-md border border-stone-200 bg-stone-50 px-3 text-sm font-normal text-stone-600" value={drawerTransaction.status} readOnly />
                </label>
              </div>
            </div>

            <div className="space-y-3 border-t border-stone-200 bg-white px-5 py-4">
              <UiButton className="w-full" icon={<Save className="h-4 w-4" />} onClick={() => { void saveRow(drawerDraftTransaction(drawerTransaction)); }} variant="primary" disabled={isBusy}>
                {asyncAction === "save" ? "Salvando..." : "Salvar alterações"}
              </UiButton>
              <div className="grid gap-2 sm:grid-cols-2">
                <UiButton icon={<Wand2 className="h-4 w-4" />} onClick={() => { void createRuleFromRow(drawerDraftTransaction(drawerTransaction)); }} variant="secondary" disabled={isBusy}>
                  {asyncAction === "rule" ? "Criando..." : "Criar regra"}
                </UiButton>
                <UiButton icon={<X className="h-4 w-4" />} onClick={() => closeDrawer()} variant="ghost" disabled={isBusy}>
                  Fechar
                </UiButton>
              </div>
              <div className="border-t border-stone-100 pt-3">
                <UiButton className="w-full" icon={<Trash2 className="h-4 w-4" />} onClick={() => requestDeleteRow(drawerTransaction)} variant="danger" disabled={isBusy}>
                  {asyncAction === "delete" ? "Excluindo..." : "Excluir transação"}
                </UiButton>
              </div>
            </div>
          </aside>
        </div>
      ) : null}

      {confirmDialog ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-4 sm:items-center">
          <div aria-labelledby="confirm-dialog-title" aria-modal="true" className="w-full max-w-md rounded-lg border border-stone-200 bg-white p-5 shadow-2xl" role="dialog">
            <h2 id="confirm-dialog-title" className="text-lg font-semibold text-ink">{confirmDialog.title}</h2>
            <p className="mt-2 text-sm leading-6 text-stone-600">{confirmDialog.description}</p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <UiButton ref={confirmCancelRef} onClick={() => closeConfirmDialog()} variant="ghost" disabled={isBusy}>
                Cancelar
              </UiButton>
              <UiButton icon={<Trash2 className="h-4 w-4" />} onClick={() => { void confirmCurrentDialog(); }} variant="danger" disabled={isBusy}>
                {asyncAction === "delete" || asyncAction === "bulk-delete" ? "Excluindo..." : confirmDialog.confirmLabel}
              </UiButton>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
