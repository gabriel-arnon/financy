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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function serverRequest<T>(path: string): Promise<T> {
  const token = (await cookies()).get("financy_access_token")?.value;
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error?.message ?? "Erro na API");
  }

  return response.json() as Promise<T>;
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
