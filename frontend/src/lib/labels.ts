import type { Account, AccountType, Card, Category, EntityStatus, TransactionType } from "@/lib/types";

export function isActiveEntity(entity: { status?: EntityStatus | string | null }): boolean {
  return entity.status !== "inactive";
}

const transactionTypeLabels: Record<TransactionType, string> = {
  expense: "Despesa",
  income: "Receita",
  transfer: "Transferência",
  payment: "Pagamento",
  refund: "Estorno"
};

export function translateTransactionType(type: TransactionType): string {
  return transactionTypeLabels[type] ?? type;
}

export function getCategoryName(categoryId: string | null | undefined, categories: Category[]): string {
  if (!categoryId) {
    return "Sem categoria";
  }

  return categories.find((category) => category.id === categoryId)?.name ?? "Sem categoria";
}

export const accountTypeLabels: Record<AccountType, string> = {
  checking: "Conta Corrente",
  savings: "Poupança",
  wallet: "Carteira",
  investment: "Investimento"
};

export function formatAccountName(account: Account): string {
  const type = accountTypeLabels[account.type] ?? account.type;
  return account.institution ? `${account.institution} - ${type}` : `${account.name} - ${type}`;
}

export function formatCardName(card: Card): string {
  const brand = card.brand ? ` ${card.brand}` : "";
  return `${card.name}${brand} ••••${card.last_digits}`;
}

export function formatCardWithAccount(card: Card, accounts: Account[]): string {
  const account = accounts.find((item) => item.id === card.account_id);
  const accountLabel = account?.institution ?? account?.name;
  return accountLabel ? `${formatCardName(card)} · ${accountLabel}` : formatCardName(card);
}

export function getAccountName(accountId: string | null | undefined, accounts: Account[]): string {
  if (!accountId) return "Sem conta";
  const account = accounts.find((item) => item.id === accountId);
  return account ? formatAccountName(account) : "Sem conta";
}

export function getCardName(cardId: string | null | undefined, cards: Card[]): string {
  if (!cardId) return "Sem cartão";
  const card = cards.find((item) => item.id === cardId);
  return card ? formatCardName(card) : "Sem cartão";
}

export function getCardNameWithAccount(cardId: string | null | undefined, cards: Card[], accounts: Account[]): string {
  if (!cardId) return "Sem cartão";
  const card = cards.find((item) => item.id === cardId);
  return card ? formatCardWithAccount(card, accounts) : "Sem cartão";
}

export function translateStatementStatus(status: string): string {
  const labels: Record<string, string> = {
    open: "Aberta",
    paid: "Paga",
    overdue: "Vencida",
    closed: "Fechada",
    partial: "Parcial"
  };
  return labels[status] ?? status;
}
