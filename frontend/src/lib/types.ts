export type TransactionType = "expense" | "income" | "transfer" | "payment" | "refund";
export type PreviewStatus = "pending" | "selected" | "ignored" | "confirmed" | "duplicate" | "error";
export type AccountType = "checking" | "savings" | "wallet" | "investment";
export type EntityStatus = "active" | "inactive";
export type ClassificationMatchScope = "description" | "original_description" | "both";
export type CategoryType = "expense" | "income" | "both";
export type ReimbursementClaimStatus = "draft" | "sent" | "acknowledged" | "disputed" | "partially_paid" | "paid" | "canceled";
export type ReimbursementItemStatus = "active" | "canceled";

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
  raw_row: Record<string, unknown> | null;
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

export interface ImportAnalysisSummary {
  item_count: number;
  selected_count: number;
  selected_total: string;
  statement_total_amount: string | null;
  difference: string | null;
  needs_review_count: number;
  duplicate_count: number;
  ai_item_count: number;
  ai_enriched_count: number;
  card_last_digits: string[];
  consistency_status: "ok" | "warning" | "unknown" | string;
  consistency_message: string | null;
  ai_summary: string | null;
}

export interface ImportPreviewResponse {
  import_id: string;
  items: ImportPreviewItem[];
  categories: Category[];
  analysis_summary: ImportAnalysisSummary | null;
}

export interface UploadImportResponse {
  import_id: string;
  file_id: string;
  filename: string;
  preview_count: number;
}

export interface StoredFile {
  id: string;
  owner_user_id: string;
  original_filename: string;
  declared_mime_type: string | null;
  detected_mime_type: string;
  size_bytes: number;
  sha256_hash: string;
  source: string;
  status: "uploaded" | "quarantined" | "available" | "rejected" | "deleted";
  scan_status: "pending" | "clean" | "suspicious" | "failed" | "skipped";
  metadata: Record<string, unknown>;
  created_at: string;
  deleted_at: string | null;
}

export interface FileSignedUrl {
  file_id: string;
  url: string;
  expires_at: string;
}

export interface TransactionAttachment {
  id: string;
  owner_user_id: string;
  transaction_id: string;
  file_id: string;
  status: EntityStatus;
  created_at: string;
  deleted_at: string | null;
  file: StoredFile;
}

export interface AiImportAnalysisResponse {
  import_id: string;
  created_preview_count: number;
  skipped: boolean;
}

export interface AiFinanceInsight {
  title: string;
  description: string;
  severity: string;
}

export interface AiSuggestedRule {
  keyword: string;
  category_id: string;
  category_name: string;
  transaction_type: TransactionType | null;
  match_count: number;
  reason: string;
}

export interface AiCategorySuggestion {
  transaction_id: string;
  description: string;
  suggested_category_id: string | null;
  suggested_category_name: string | null;
  reason: string;
}

export interface AiRecurrenceSuggestion {
  description: string;
  amount: string;
  transaction_type: TransactionType;
  occurrences: number;
  cadence: string;
  reason: string;
}

export interface AiRenameSuggestion {
  transaction_id: string;
  current_description: string;
  suggested_description: string;
  reason: string;
}

export interface AiFinanceOverview {
  summary: string;
  insights: AiFinanceInsight[];
  suggested_rules: AiSuggestedRule[];
  category_suggestions: AiCategorySuggestion[];
  recurrence_suggestions: AiRecurrenceSuggestion[];
  rename_suggestions: AiRenameSuggestion[];
}

export interface AiFinanceQuestionResponse {
  answer: string;
  matched_count: number;
  total_amount: string | null;
  filters: string[];
  message?: string | null;
  kind?: string;
  summary?: {
    matched_count: number;
    total_amount: string | null;
    currency: string;
    period_label: string | null;
  } | null;
  cta?: {
    label: string;
    route: string;
    query: Record<string, string>;
  } | null;
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
  account: Account | null;
  limit_total: string | null;
  limit_used: string;
  limit_available: string | null;
  usage_percent: string | null;
  upcoming_statements: CardSummaryStatement[];
  statement_history: CardSummaryStatement[];
  recent_transactions: CardSummaryTransaction[];
}

export interface ReimbursementContact {
  id: string;
  owner_user_id: string;
  display_name: string;
  email: string | null;
  phone: string | null;
  status: EntityStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
}

export interface ReimbursementContactPayload {
  display_name: string;
  email?: string | null;
  phone?: string | null;
  status?: EntityStatus;
}

export interface ReimbursementItem {
  id: string;
  owner_user_id: string;
  claim_id: string;
  transaction_id: string;
  amount_requested: string;
  status: ReimbursementItemStatus;
  transaction_snapshot: Record<string, unknown>;
  snapshot_is_current: boolean | null;
  position: number;
  canceled_at: string | null;
  created_at: string;
}

export interface ReimbursementClaim {
  id: string;
  owner_user_id: string;
  contact_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: ReimbursementClaimStatus;
  total_snapshot: string | null;
  total_amount: string;
  version: number;
  sent_at: string | null;
  canceled_at: string | null;
  first_viewed_at: string | null;
  last_viewed_at: string | null;
  view_count: number;
  created_at: string;
  updated_at: string | null;
  contact: ReimbursementContact | null;
  items: ReimbursementItem[];
}

export interface ReimbursementClaimPayload {
  contact_id: string;
  title: string;
  description?: string | null;
  due_date?: string | null;
}

export interface ReimbursementOverview {
  total_sent: string;
  draft_count: number;
  sent_count: number;
  canceled_count: number;
  recent_claims: ReimbursementClaim[];
  draft_claims: ReimbursementClaim[];
  upcoming_claims: ReimbursementClaim[];
}

export interface ReimbursementEligibleTransaction {
  id: string;
  transaction_date: string;
  description: string;
  amount: string;
  type: string;
  status: string;
  category_id: string | null;
  account_id: string | null;
  card_id: string | null;
  card_statement_id: string | null;
  allocated_amount: string;
  available_amount: string;
  eligible: boolean;
  ineligible_reason: string | null;
}

export interface ReimbursementEvent {
  id: string;
  owner_user_id: string;
  claim_id: string | null;
  contact_id: string | null;
  item_id: string | null;
  actor_type: "owner" | "guest" | "system";
  actor_user_id: string | null;
  event_type: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ReimbursementInvitation {
  id: string;
  owner_user_id: string;
  contact_id: string;
  claim_id: string | null;
  email: string;
  status: "pending" | "accepted" | "revoked" | "expired";
  expires_at: string;
  accepted_at: string | null;
  accepted_by_user_id: string | null;
  revoked_at: string | null;
  created_at: string;
  contact: ReimbursementContact | null;
  claim: ReimbursementClaim | null;
}

export interface ReimbursementInvitationCreated extends ReimbursementInvitation {
  accept_token: string;
  accept_path: string;
}

export interface ReimbursementMembership {
  id: string;
  owner_user_id: string;
  contact_id: string;
  auth_user_id: string;
  email: string | null;
  status: "active" | "revoked";
  linked_at: string;
  revoked_at: string | null;
  created_at: string;
  contact: ReimbursementContact | null;
}

export interface ReimbursementClaimAttachment {
  id: string;
  claim_id: string;
  status: EntityStatus;
  created_at: string;
  deleted_at: string | null;
  file: {
    original_filename: string;
    detected_mime_type: string;
    size_bytes: number;
  };
}

export interface GuestReimbursementItem {
  id: string;
  description: string;
  transaction_date: string;
  amount: string;
  amount_requested: string;
  currency: string;
}

export interface GuestReimbursementClaim {
  id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: ReimbursementClaimStatus;
  total_amount: string;
  sent_at: string | null;
  first_viewed_at: string | null;
  last_viewed_at: string | null;
  attachment_count: number;
  items: GuestReimbursementItem[];
}
