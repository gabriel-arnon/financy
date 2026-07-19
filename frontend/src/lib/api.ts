import type {
  Account,
  AccountPayload,
  AccountSummary,
  AiFinanceOverview,
  AiFinanceQuestionResponse,
  AiImportAnalysisResponse,
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
  GuestReimbursementClaim,
  OpenFinanceConnectToken,
  OpenFinanceItem,
  PlanningOverview,
  OpenFinanceStatus,
  OpenFinanceSyncResponse,
  OpenFinanceSyncRun,
  Budget,
  BudgetPayload,
  FinancialGoal,
  FinancialGoalPayload,
  RecurringItem,
  RecurringItemPayload,
  ReimbursementClaim,
  ReimbursementClaimAttachment,
  ReimbursementComment,
  ReimbursementClaimPayload,
  ReimbursementContact,
  ReimbursementContactPayload,
  ReimbursementEligibleTransaction,
  ReimbursementEvent,
  ReimbursementInvitation,
  ReimbursementInvitationCreated,
  ReimbursementMembership,
  ReimbursementOverview,
  Transaction,
  TransactionAttachment,
  TransactionPayload,
  FileSignedUrl,
  StoredFile,
  UploadImportResponse
} from "@/lib/types";
import { resolveApiBaseUrl } from "@/lib/api-url";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";

const API_URL = resolveApiBaseUrl("Financy client API");
const RETRY_DELAYS_MS = [600, 1500, 3000];
const RETRYABLE_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504]);

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function requestMethod(init?: RequestInit) {
  return (init?.method ?? "GET").toUpperCase();
}

export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function canRetry(path: string, init?: RequestInit) {
  if (path === "/open-finance/status") return false;
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
  const { data } = await requestWithResponse<T>(path, init);
  return data;
}

async function requestWithResponse<T>(path: string, init?: RequestInit): Promise<{ data: T; response: Response }> {
  const token = await accessToken();
  const headers: HeadersInit = {
    ...(init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers }),
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
  const retryable = canRetry(path, init);
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
      return { data: await response.json() as T, response };
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
    throw new ApiError(body?.error?.message ?? `Erro na API (${response.status})`, response.status, body?.error?.code ?? null);
  }

  throw new Error("Falha inesperada ao chamar a API.");
}

export async function uploadImport(file: File): Promise<UploadImportResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadImportResponse>("/imports/upload", { method: "POST", body: form });
}

export async function uploadPrivateFile(file: File, source = "manual"): Promise<StoredFile> {
  const form = new FormData();
  form.append("file", file);
  return request<StoredFile>(`/files/upload?source=${encodeURIComponent(source)}`, { method: "POST", body: form });
}

export async function getFileSignedUrl(fileId: string): Promise<FileSignedUrl> {
  return request<FileSignedUrl>(`/files/${fileId}/signed-url`);
}

export async function deletePrivateFile(fileId: string): Promise<StoredFile> {
  return request<StoredFile>(`/files/${fileId}`, { method: "DELETE" });
}

export async function getTransactionAttachments(transactionId: string): Promise<TransactionAttachment[]> {
  return request<TransactionAttachment[]>(`/transactions/${transactionId}/attachments`);
}

export async function attachFileToTransaction(transactionId: string, fileId: string): Promise<TransactionAttachment> {
  return request<TransactionAttachment>(`/transactions/${transactionId}/attachments`, {
    method: "POST",
    body: JSON.stringify({ file_id: fileId })
  });
}

export async function deleteTransactionAttachment(transactionId: string, attachmentId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/transactions/${transactionId}/attachments/${attachmentId}`, { method: "DELETE" });
}

export async function getImportPreview(importId: string): Promise<ImportPreviewResponse> {
  return request<ImportPreviewResponse>(`/imports/${importId}/preview`);
}

export async function analyzeImportWithAi(importId: string): Promise<AiImportAnalysisResponse> {
  return request<AiImportAnalysisResponse>(`/imports/${importId}/analyze-ai`, { method: "POST" });
}

export async function getAiFinanceOverview(): Promise<AiFinanceOverview> {
  return request<AiFinanceOverview>("/ai-finance/overview");
}

export async function getOpenFinanceStatus(): Promise<OpenFinanceStatus> {
  return request<OpenFinanceStatus>("/open-finance/status");
}

export async function getOpenFinanceItems(): Promise<OpenFinanceItem[]> {
  return request<OpenFinanceItem[]>("/open-finance/items");
}

export async function createOpenFinanceItem(externalItemId: string): Promise<OpenFinanceItem> {
  return request<OpenFinanceItem>("/open-finance/items", {
    method: "POST",
    body: JSON.stringify({ external_item_id: externalItemId })
  });
}

export async function createOpenFinanceConnectToken(): Promise<OpenFinanceConnectToken> {
  return request<OpenFinanceConnectToken>("/open-finance/connect-token", { method: "POST" });
}

export async function syncOpenFinance(): Promise<OpenFinanceSyncResponse> {
  return request<OpenFinanceSyncResponse>("/open-finance/sync", { method: "POST" });
}

export async function syncOpenFinanceItem(externalItemId: string): Promise<OpenFinanceSyncResponse> {
  return request<OpenFinanceSyncResponse>(`/open-finance/items/${encodeURIComponent(externalItemId)}/sync`, { method: "POST" });
}

export async function getOpenFinanceSyncRuns(): Promise<OpenFinanceSyncRun[]> {
  return request<OpenFinanceSyncRun[]>("/open-finance/sync-runs");
}

export async function getPlanningOverview(periodMonth?: string): Promise<PlanningOverview> {
  return request<PlanningOverview>(`/planning/overview${periodMonth ? `?period_month=${encodeURIComponent(periodMonth)}` : ""}`);
}

export async function createRecurringItem(payload: RecurringItemPayload): Promise<RecurringItem> {
  return request<RecurringItem>("/planning/recurring-items", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateRecurringItem(recurringItemId: string, payload: Partial<RecurringItemPayload>): Promise<RecurringItem> {
  return request<RecurringItem>(`/planning/recurring-items/${recurringItemId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteRecurringItem(recurringItemId: string): Promise<RecurringItem> {
  return request<RecurringItem>(`/planning/recurring-items/${recurringItemId}`, { method: "DELETE" });
}

export async function createFinancialGoal(payload: FinancialGoalPayload): Promise<FinancialGoal> {
  return request<FinancialGoal>("/planning/goals", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateFinancialGoal(goalId: string, payload: Partial<FinancialGoalPayload>): Promise<FinancialGoal> {
  return request<FinancialGoal>(`/planning/goals/${goalId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteFinancialGoal(goalId: string): Promise<FinancialGoal> {
  return request<FinancialGoal>(`/planning/goals/${goalId}`, { method: "DELETE" });
}

export async function createBudget(payload: BudgetPayload): Promise<Budget> {
  return request<Budget>("/planning/budgets", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateBudget(budgetId: string, payload: Partial<BudgetPayload>): Promise<Budget> {
  return request<Budget>(`/planning/budgets/${budgetId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteBudget(budgetId: string): Promise<Budget> {
  return request<Budget>(`/planning/budgets/${budgetId}`, { method: "DELETE" });
}

export async function askAiFinance(question: string): Promise<AiFinanceQuestionResponse> {
  return request<AiFinanceQuestionResponse>("/ai-finance/ask", {
    method: "POST",
    body: JSON.stringify({ question })
  });
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

export async function getReimbursementOverview(): Promise<ReimbursementOverview> {
  return request<ReimbursementOverview>("/reimbursements/overview");
}

export async function getReimbursementContacts(): Promise<ReimbursementContact[]> {
  return request<ReimbursementContact[]>("/reimbursements/contacts");
}

export async function createReimbursementContact(payload: ReimbursementContactPayload): Promise<ReimbursementContact> {
  return request<ReimbursementContact>("/reimbursements/contacts", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateReimbursementContact(contactId: string, payload: Partial<ReimbursementContactPayload>): Promise<ReimbursementContact> {
  return request<ReimbursementContact>(`/reimbursements/contacts/${contactId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function deleteReimbursementContact(contactId: string): Promise<ReimbursementContact> {
  return request<ReimbursementContact>(`/reimbursements/contacts/${contactId}`, { method: "DELETE" });
}

export async function getReimbursementClaims(): Promise<ReimbursementClaim[]> {
  return request<ReimbursementClaim[]>("/reimbursements/claims");
}

export async function createReimbursementClaim(payload: ReimbursementClaimPayload): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>("/reimbursements/claims", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateReimbursementClaim(claimId: string, payload: Partial<ReimbursementClaimPayload>): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function addReimbursementItem(claimId: string, payload: { transaction_id: string; amount_requested: string }): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}/items`, { method: "POST", body: JSON.stringify(payload) });
}

export async function updateReimbursementItem(claimId: string, itemId: string, payload: { amount_requested: string }): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}/items/${itemId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function deleteReimbursementItem(claimId: string, itemId: string): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}/items/${itemId}`, { method: "DELETE" });
}

export async function sendReimbursementClaim(claimId: string): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}/send`, { method: "POST" });
}

export async function cancelReimbursementClaim(claimId: string): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}/cancel`, { method: "POST" });
}

export async function refreshReimbursementSnapshots(claimId: string): Promise<ReimbursementClaim> {
  return request<ReimbursementClaim>(`/reimbursements/claims/${claimId}/refresh-snapshots`, { method: "POST" });
}

export async function getReimbursementEvents(claimId: string): Promise<ReimbursementEvent[]> {
  return request<ReimbursementEvent[]>(`/reimbursements/claims/${claimId}/events`);
}

export async function getReimbursementComments(claimId: string, params?: { limit?: number; cursor?: string | null }): Promise<ReimbursementComment[]> {
  const search = new URLSearchParams();
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.cursor) search.set("cursor", params.cursor);
  const query = search.toString();
  return request<ReimbursementComment[]>(`/reimbursements/claims/${claimId}/comments${query ? `?${query}` : ""}`);
}

export async function createReimbursementComment(claimId: string, body: string): Promise<ReimbursementComment> {
  return request<ReimbursementComment>(`/reimbursements/claims/${claimId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body })
  });
}

export async function deleteReimbursementComment(claimId: string, commentId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/reimbursements/claims/${claimId}/comments/${commentId}`, { method: "DELETE" });
}

export async function addReimbursementClaimAttachment(claimId: string, fileId: string): Promise<ReimbursementClaimAttachment> {
  return request<ReimbursementClaimAttachment>(`/reimbursements/claims/${claimId}/attachments`, { method: "POST", body: JSON.stringify({ file_id: fileId }) });
}

export async function getReimbursementClaimAttachments(claimId: string): Promise<ReimbursementClaimAttachment[]> {
  return request<ReimbursementClaimAttachment[]>(`/reimbursements/claims/${claimId}/attachments`);
}

export async function deleteReimbursementClaimAttachment(claimId: string, attachmentId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/reimbursements/claims/${claimId}/attachments/${attachmentId}`, { method: "DELETE" });
}

export async function getReimbursementInvitations(): Promise<ReimbursementInvitation[]> {
  return request<ReimbursementInvitation[]>("/reimbursements/invitations");
}

export async function createReimbursementInvitation(payload: {
  contact_id: string;
  claim_id?: string | null;
  email?: string | null;
  expires_in_days?: number;
}): Promise<ReimbursementInvitationCreated> {
  return request<ReimbursementInvitationCreated>("/reimbursements/invitations", { method: "POST", body: JSON.stringify(payload) });
}

export async function revokeReimbursementInvitation(invitationId: string): Promise<ReimbursementInvitation> {
  return request<ReimbursementInvitation>(`/reimbursements/invitations/${invitationId}/revoke`, { method: "POST" });
}

export async function getReimbursementMemberships(): Promise<ReimbursementMembership[]> {
  return request<ReimbursementMembership[]>("/reimbursements/memberships");
}

export async function revokeReimbursementMembership(membershipId: string): Promise<ReimbursementMembership> {
  return request<ReimbursementMembership>(`/reimbursements/memberships/${membershipId}/revoke`, { method: "POST" });
}

export async function acceptReimbursementInvitation(token: string): Promise<ReimbursementMembership> {
  return request<ReimbursementMembership>("/reimbursements/guest/invitations/accept", { method: "POST", body: JSON.stringify({ token }) });
}

export async function getGuestReimbursementClaims(): Promise<GuestReimbursementClaim[]> {
  return request<GuestReimbursementClaim[]>("/reimbursements/guest/claims");
}

export async function getGuestReimbursementClaim(claimId: string): Promise<GuestReimbursementClaim> {
  return request<GuestReimbursementClaim>(`/reimbursements/guest/claims/${claimId}`);
}

export async function acknowledgeGuestReimbursementClaim(claimId: string): Promise<GuestReimbursementClaim> {
  return request<GuestReimbursementClaim>(`/reimbursements/guest/claims/${claimId}/acknowledge`, { method: "POST" });
}

export async function disputeGuestReimbursementClaim(claimId: string, note?: string): Promise<GuestReimbursementClaim> {
  return request<GuestReimbursementClaim>(`/reimbursements/guest/claims/${claimId}/dispute`, { method: "POST", body: JSON.stringify({ note: note ?? null }) });
}

export async function getGuestReimbursementClaimAttachments(claimId: string): Promise<ReimbursementClaimAttachment[]> {
  return request<ReimbursementClaimAttachment[]>(`/reimbursements/guest/claims/${claimId}/attachments`);
}

export async function getGuestReimbursementClaimAttachmentSignedUrl(claimId: string, attachmentId: string): Promise<FileSignedUrl> {
  return request<FileSignedUrl>(`/reimbursements/guest/claims/${claimId}/attachments/${attachmentId}/signed-url`);
}

export async function getReimbursementEligibleTransactions(params?: { q?: string; limit?: number }): Promise<ReimbursementEligibleTransaction[]> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.limit) search.set("limit", String(params.limit));
  const query = search.toString();
  return request<ReimbursementEligibleTransaction[]>(`/reimbursements/eligible-transactions${query ? `?${query}` : ""}`);
}

export async function getCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function createCategory(payload: CategoryPayload): Promise<Category & { action?: "created" | "reactivated" }> {
  const { data, response } = await requestWithResponse<Category>("/categories", { method: "POST", body: JSON.stringify(payload) });
  const action = response.headers.get("X-Financy-Category-Action");
  return { ...data, action: action === "reactivated" ? "reactivated" : "created" };
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
