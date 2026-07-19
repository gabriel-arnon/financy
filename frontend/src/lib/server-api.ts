import { cookies } from "next/headers";
import type {
  Account,
  AccountSummary,
  Card,
  CardSummary,
  CardStatementDetail,
  CardStatementSummary,
  Category,
  ClassificationRule
} from "@/lib/types";
import { resolveApiBaseUrl } from "@/lib/api-url";

const API_URL = resolveApiBaseUrl("Financy server API");
const RETRY_DELAYS_MS = [600, 1500, 3000];
const RETRYABLE_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504]);

function createRequestId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `financy-server-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function logServerApiFailure(details: {
  path: string;
  requestId: string;
  attempt: number;
  status?: number;
  message: string;
}) {
  console.warn("Financy server API request failed", {
    path: details.path,
    method: "GET",
    request_id: details.requestId,
    attempt: details.attempt,
    status: details.status,
    message: details.message
  });
}

async function serverRequest<T>(path: string): Promise<T> {
  const token = (await cookies()).get("financy_access_token")?.value;
  const requestId = createRequestId();
  const attempts = RETRY_DELAYS_MS.length + 1;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        headers: {
          "X-Request-Id": requestId,
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        cache: "no-store"
      });
    } catch (err) {
      if (attempt < attempts - 1) {
        await sleep(RETRY_DELAYS_MS[attempt]);
        continue;
      }
      const detail = err instanceof Error && err.message ? ` Detalhe: ${err.message}` : "";
      const message = `Falha de conexao com a API em ${path}. Request ID: ${requestId}.${detail}`;
      logServerApiFailure({ path, requestId, attempt: attempt + 1, message });
      throw new Error(message);
    }

    if (response.ok) {
      return response.json() as Promise<T>;
    }

    if (RETRYABLE_STATUS_CODES.has(response.status) && attempt < attempts - 1) {
      logServerApiFailure({
        path,
        requestId,
        attempt: attempt + 1,
        status: response.status,
        message: `Retryable API status ${response.status}`
      });
      await sleep(RETRY_DELAYS_MS[attempt]);
      continue;
    }

    const body = await response.json().catch(() => null);
    const responseRequestId = response.headers.get("X-Request-Id") ?? body?.error?.request_id ?? requestId;
    logServerApiFailure({
      path,
      requestId: responseRequestId,
      attempt: attempt + 1,
      status: response.status,
      message: body?.error?.message ?? `Erro na API (${response.status})`
    });
    throw new Error(body?.error?.message ?? `Erro na API (${response.status})`);
  }

  throw new Error("Falha inesperada ao chamar a API.");
}

export async function serverGetCategories(): Promise<Category[]> {
  return serverRequest<Category[]>("/categories");
}

export async function serverGetAccounts(): Promise<Account[]> {
  return serverRequest<Account[]>("/accounts");
}

export async function serverGetCards(): Promise<Card[]> {
  return serverRequest<Card[]>("/cards");
}

export async function serverGetStatements(): Promise<CardStatementSummary[]> {
  return serverRequest<CardStatementSummary[]>("/statements");
}

export async function serverGetClassificationRules(): Promise<ClassificationRule[]> {
  return serverRequest<ClassificationRule[]>("/classification-rules");
}

export async function serverGetAccountSummary(accountId: string, params?: { start_date?: string; end_date?: string }): Promise<AccountSummary> {
  const search = new URLSearchParams();
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);
  const query = search.toString();
  return serverRequest<AccountSummary>(`/accounts/${accountId}/summary${query ? `?${query}` : ""}`);
}

export async function serverGetCardSummary(cardId: string): Promise<CardSummary> {
  return serverRequest<CardSummary>(`/cards/${cardId}/summary`);
}

export async function serverGetStatement(statementId: string): Promise<CardStatementDetail> {
  return serverRequest<CardStatementDetail>(`/statements/${statementId}`);
}
