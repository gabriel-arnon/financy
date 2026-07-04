export type TransactionType = "expense" | "income" | "transfer" | "payment" | "refund";
export type PreviewStatus = "pending" | "selected" | "ignored" | "confirmed" | "duplicate" | "error";
export type AccountType = "checking" | "savings" | "wallet" | "investment";
export type EntityStatus = "active" | "inactive";
export type ClassificationMatchScope = "description" | "original_description" | "both";
export type CategoryType = "expense" | "income" | "both";

export interface Category {
  id: string;
  user_id?: string | null;
  name: string;
  type: CategoryType;
  status: EntityStatus;
  is_system?: boolean;
  created_at?: string | null;
}

export interface CategoryPayload {
  name: string;
  type: CategoryType;
  status: EntityStatus;
}

export interface Account {
  id: string;
  user_id: string;
  name: string;
  institution: string | null;
  agency: string | null;
  account_number: string | null;
  type: AccountType;
  balance: string;
  status: EntityStatus;
  created_at: string;
}

export interface AccountPayload {
  name: string;
  institution: string | null;
  agency?: string | null;
  account_number?: string | null;
  type: AccountType;
  balance: string;
  status: EntityStatus;
}

export interface Card {
  id: string;
  user_id: string;
  account_id: string | null;
  name: string;
  institution: string | null;
  brand: string | null;
  last_digits: string;
  limit_amount: string | null;
  closing_day: number | null;
  due_day: number | null;
  status: EntityStatus;
  created_at: string;
}

export interface CardPayload {
  account_id: string | null;
  name: string;
  institution: string | null;
  brand: string | null;
  last_digits: string;
  limit_amount: string | null;
  closing_day: number | null;
  due_day: number | null;
  status: EntityStatus;
}

export interface ClassificationRule {
  id: string;
  user_id: string;
  keyword: string;
  category_id: string;
  transaction_type: TransactionType | null;
  priority: number;
  status: EntityStatus;
  match_scope: ClassificationMatchScope;
  auto_created: boolean;
  created_at: string;
}

export interface ClassificationRulePayload {
  keyword: string;
  category_id: string;
  transaction_type: TransactionType | null;
  priority: number;
  status: EntityStatus;
  match_scope: ClassificationMatchScope;
  auto_created: boolean;
}

export interface ImportPreviewItem {
  id: string;
  transaction_date: string;
  description: string;
  original_description: string;
  amount: string;
  type: TransactionType;
  category_id: string | null;
  suggested_category: string | null;
  merchant_country: string | null;
  account_id: string | null;
  card_id: string | null;
  card_statement_id: string | null;
  installment_current: number | null;
  installment_total: number | null;
  raw_text: string | null;
  parser_confidence: number;
  needs_review: boolean;
  duplicate_candidate: boolean;
  default_selected: boolean;
  excluded_reason: string | null;
  classification_rule_id: string | null;
  classification_label: string | null;
  statement_total_amount: string | null;
  statement_due_date: string | null;
  statement_reference_month: string | null;
  card_last_digits: string | null;
  card_name: string | null;
  card_brand: string | null;
  card_institution: string | null;
  card_limit_amount: string | null;
  account_institution: string | null;
  account_agency: string | null;
  account_number: string | null;
  account_balance: string | null;
  status: PreviewStatus;
}

export interface ImportPreviewResponse {
  import_id: string;
  items: ImportPreviewItem[];
  categories: Category[];
}

export interface UploadImportResponse {
  import_id: string;
  file_id: string;
  filename: string;
  preview_count: number;
}

export interface ConfirmImportResponse {
  import_id: string;
  created_transaction_ids: string[];
  duplicate_preview_item_ids: string[];
  ignored_preview_item_ids: string[];
  confirmed_at: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  account_id: string | null;
  card_id: string | null;
  card_statement_id: string | null;
  transaction_date: string;
  description: string;
  original_description: string | null;
  normalized_description: string;
  amount: string;
  type: TransactionType;
  category_id: string | null;
  source_file_id: string | null;
  installment_current: number | null;
  installment_total: number | null;
  status: string;
  created_at: string;
}

export interface TransactionPayload {
  account_id?: string | null;
  card_id?: string | null;
  card_statement_id?: string | null;
  transaction_date?: string;
  description?: string;
  original_description?: string | null;
  amount?: string;
  type?: TransactionType;
  category_id?: string | null;
  source_file_id?: string | null;
  installment_current?: number | null;
  installment_total?: number | null;
  status?: string;
}

export interface CardStatementSummary {
  id: string;
  user_id: string;
  card_id: string;
  account_id: string | null;
  reference_month: string;
  due_date: string | null;
  closing_date: string | null;
  reported_total: string | null;
  minimum_payment_amount: string | null;
  status: string;
  paid_at: string | null;
  source_file_id: string | null;
  transaction_count: number;
  calculated_total: string;
  difference: string | null;
  integrity_status: "ok" | "no_transactions" | "difference";
  integrity_label: string;
  created_at: string;
}

export interface CardStatementDetail extends CardStatementSummary {
  transactions: Transaction[];
}

export interface AccountSummaryCard extends Card {
  open_statement_count: number;
  open_statement_total: string;
}

export interface AccountSummary {
  account: Account;
  cards: AccountSummaryCard[];
  open_statements: CardStatementSummary[];
  total_open_statements: string;
  total_open_statements_ok: string;
  total_open_statements_warning: string;
  transaction_count: number;
  total_income: string;
  total_expense: string;
  net_balance_period: string;
  recent_transactions: Transaction[];
}

export interface CardSummaryStatement {
  id: string;
  reference_month: string;
  due_date: string | null;
  status: string;
  reported_total: string | null;
  calculated_total: string;
  difference: string | null;
  integrity_status: "ok" | "no_transactions" | "difference";
  transaction_count: number;
}

export type CardSummaryTransaction = Transaction;

export interface CardSummary {
  card: Card;
  account: Account;
  limit_total: string | null;
  limit_used: string;
  limit_available: string | null;
  usage_percent: string | null;
  upcoming_statements: CardSummaryStatement[];
  statement_history: CardSummaryStatement[];
  recent_transactions: CardSummaryTransaction[];
}
