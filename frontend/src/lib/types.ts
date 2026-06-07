export type TransactionType = "expense" | "income" | "transfer" | "payment" | "refund";
export type PreviewStatus = "pending" | "selected" | "ignored" | "confirmed" | "duplicate" | "error";

export interface Category {
  id: string;
  name: string;
}

export interface ImportPreviewItem {
  id: string;
  transaction_date: string;
  description: string;
  original_description: string;
  amount: string;
  type: TransactionType;
  category_id: string | null;
  account_id: string | null;
  card_id: string | null;
  card_statement_id: string | null;
  installment_current: number | null;
  installment_total: number | null;
  raw_text: string | null;
  parser_confidence: number;
  needs_review: boolean;
  duplicate_candidate: boolean;
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
