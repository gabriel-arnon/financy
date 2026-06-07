import type { ImportPreviewResponse, Transaction, UploadImportResponse } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error?.message ?? "Erro na API");
  }

  return response.json() as Promise<T>;
}

export async function uploadImport(file: File): Promise<UploadImportResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadImportResponse>("/imports/upload", { method: "POST", body: form });
}

export async function getImportPreview(importId: string): Promise<ImportPreviewResponse> {
  return request<ImportPreviewResponse>(`/imports/${importId}/preview`);
}

export async function confirmImport(importId: string, items: unknown[]) {
  return request(`/imports/${importId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ items })
  });
}

export async function getTransactions(): Promise<Transaction[]> {
  return request<Transaction[]>("/transactions");
}
