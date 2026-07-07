import type {
  Account,
  AccountPayload,
  AccountSummary,
  Card,
  CardPayload,
  CardSummary,
  CardStatementDetail,
  CardStatementSummary,
  Category,
  CategoryPayload,
  ClassificationRule,
  ClassificationRulePayload,
  ConfirmImportResponse,
  ImportPreviewResponse,
  Transaction,
  TransactionPayload,
  UploadImportResponse
} from "@/lib/types";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const RETRY_DELAYS_MS = [600, 1500, 3000];
const RETRYABLE_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504]);

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function requestMethod(init?: RequestInit) {
  return (init?.method ?? "GET").toUpperCase();
}

function canRetry(init?: RequestInit) {
  const method = requestMethod(init);
  return method === "GET" || method === "HEAD";
}

function networkErrorMessage(path: string, err: unknown) {
  const detail = err instanceof Error && err.message ? ` Detalhe: ${err.message}` : "";
  return `Falha de conexao com a API em ${path}. Tente novamente em alguns segundos.${detail}`;
}

async function accessToken(): Promise<string | null> {
  if (typeof window === "undefined" || !isSupabaseConfigured()) return null;
  const supabase = getSupabaseClient();
  const { data } = await supabase!.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await accessToken();
  const headers: HeadersInit = {
    ...(init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers }),
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
  const retryable = canRetry(init);
  const attempts = retryable ? RETRY_DELAYS_MS.length + 1 : 1;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        ...init,
        headers,
        cache: "no-store"
      });
    } catch (err) {
      if (retryable && attempt < attempts - 1) {
        await sleep(RETRY_DELAYS_MS[attempt]);
        continue;
      }
      throw new Error(networkErrorMessage(path, err));
    }

    if (response.ok) {
      return response.json() as Promise<T>;
    }

    if (retryable && RETRYABLE_STATUS_CODES.has(response.status) && attempt < attempts - 1) {
      await sleep(RETRY_DELAYS_MS[attempt]);
      continue;
    }

    const body = await response.json().catch(() => null);
    if (response.status === 401 && typeof window !== "undefined" && isSupabaseConfigured()) {
      const supabase = getSupabaseClient();
      await supabase?.auth.signOut();
      document.cookie = "financy_access_token=; Path=/; Max-Age=0; SameSite=Lax";
      window.location.assign("/login");
    }
    throw new Error(body?.error?.message ?? `Erro na API (${response.status})`);
  }

  throw new Error("Falha inesperada ao chamar a API.");
}

export async function uploadImport(file: File): Promise<UploadImportResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadImportResponse>("/imports/upload", { method: "POST", body: form });
}

export async function getImportPreview(importId: string): Promise<ImportPreviewResponse> {
  return request<ImportPreviewResponse>(`/imports/${importId}/preview`);
}

export async function confirmImport(importId: string, items: unknown[]): Promise<ConfirmImportResponse> {
  return request<ConfirmImportResponse>(`/imports/${importId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ items })
  });
}

export async function getTransactions(): Promise<Transaction[]> {
  return request<Transaction[]>("/transactions");
}

export async function createTransaction(payload: TransactionPayload): Promise<Transaction> {
  return request<Transaction>("/transactions", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateTransaction(transactionId: string, payload: TransactionPayload): Promise<Transaction> {
  return request<Transaction>(`/transactions/${transactionId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteTransaction(transactionId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/transactions/${transactionId}`, { method: "DELETE" });
}

export async function getCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function createCategory(payload: CategoryPayload): Promise<Category> {
  return request<Category>("/categories", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateCategory(categoryId: string, payload: Partial<CategoryPayload>): Promise<Category> {
  return request<Category>(`/categories/${categoryId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteCategory(categoryId: string): Promise<Category> {
  return request<Category>(`/categories/${categoryId}`, { method: "DELETE" });
}

export async function getAccounts(): Promise<Account[]> {
  return request<Account[]>("/accounts");
}

export async function getAccountSummary(accountId: string, params?: { start_date?: string; end_date?: string }): Promise<AccountSummary> {
  const search = new URLSearchParams();
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);
  const query = search.toString();
  return request<AccountSummary>(`/accounts/${accountId}/summary${query ? `?${query}` : ""}`);
}

export async function createAccount(payload: AccountPayload): Promise<Account> {
  return request<Account>("/accounts", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateAccount(accountId: string, payload: Partial<AccountPayload>): Promise<Account> {
  return request<Account>(`/accounts/${accountId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteAccount(accountId: string): Promise<Account> {
  return request<Account>(`/accounts/${accountId}`, { method: "DELETE" });
}

export async function getCards(): Promise<Card[]> {
  return request<Card[]>("/cards");
}

export async function getCardSummary(cardId: string): Promise<CardSummary> {
  return request<CardSummary>(`/cards/${cardId}/summary`);
}

export async function createCard(payload: CardPayload): Promise<Card> {
  return request<Card>("/cards", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateCard(cardId: string, payload: Partial<CardPayload>): Promise<Card> {
  return request<Card>(`/cards/${cardId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteCard(cardId: string): Promise<Card> {
  return request<Card>(`/cards/${cardId}`, { method: "DELETE" });
}

export async function getStatements(): Promise<CardStatementSummary[]> {
  return request<CardStatementSummary[]>("/statements");
}

export async function getStatement(statementId: string): Promise<CardStatementDetail> {
  return request<CardStatementDetail>(`/statements/${statementId}`);
}

export async function updateStatementStatus(statementId: string, status: "open" | "paid" | "overdue", paidAt?: string): Promise<CardStatementDetail> {
  return request<CardStatementDetail>(`/statements/${statementId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, paid_at: paidAt })
  });
}

export async function deleteStatement(statementId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/statements/${statementId}`, { method: "DELETE" });
}

export async function getClassificationRules(): Promise<ClassificationRule[]> {
  return request<ClassificationRule[]>("/classification-rules");
}

export async function createClassificationRule(payload: ClassificationRulePayload): Promise<ClassificationRule> {
  return request<ClassificationRule>("/classification-rules", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateClassificationRule(ruleId: string, payload: Partial<ClassificationRulePayload>): Promise<ClassificationRule> {
  return request<ClassificationRule>(`/classification-rules/${ruleId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteClassificationRule(ruleId: string): Promise<ClassificationRule> {
  return request<ClassificationRule>(`/classification-rules/${ruleId}`, { method: "DELETE" });
}
