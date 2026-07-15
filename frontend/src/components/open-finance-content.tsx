"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Activity, AlertCircle, CheckCircle2, Landmark, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import type { ProductType } from "pluggy-js";
import { UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";
import {
  createOpenFinanceConnectToken,
  createOpenFinanceItem,
  getOpenFinanceItems,
  getOpenFinanceStatus,
  getOpenFinanceSyncRuns,
  syncOpenFinance,
  syncOpenFinanceItem
} from "@/lib/api";
import { cn } from "@/lib/classnames";
import type { OpenFinanceItem, OpenFinanceStatus, OpenFinanceSyncRun } from "@/lib/types";

const PluggyConnect = dynamic(() => import("react-pluggy-connect").then((mod) => mod.PluggyConnect), { ssr: false });
const OPEN_FINANCE_PRODUCTS: ProductType[] = ["ACCOUNTS", "CREDIT_CARDS", "TRANSACTIONS"];

function formatDateTime(value: string | null) {
  if (!value) return "Nunca";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function statusClass(status: string) {
  if (status === "success" || status === "active" || status === "updated") return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (status === "running") return "bg-blue-50 text-blue-700 ring-blue-200";
  if (status === "error" || status === "failed") return "bg-red-50 text-red-700 ring-red-200";
  return "bg-stone-100 text-stone-700 ring-stone-200";
}

function formatIgnoredReasons(reasons: Record<string, number> | undefined) {
  if (!reasons || Object.keys(reasons).length === 0) return null;
  const labels: Record<string, string> = {
    duplicate_signature: "duplicadas",
    missing_transaction_identifier: "sem identificador",
    transactions_unavailable: "indisponiveis"
  };
  return Object.entries(reasons)
    .map(([reason, count]) => `${count} ${labels[reason] ?? reason}`)
    .join(", ");
}

function formatAccountErrors(errors: OpenFinanceSyncRun["metadata"]["transaction_account_errors"]) {
  if (!errors || errors.length === 0) return null;
  return errors
    .slice(0, 2)
    .map((error) => {
      const account = error.account_name || error.account_id || "conta";
      const code = error.status_code ? `HTTP ${error.status_code}` : "erro";
      return `${account}: ${code}`;
    })
    .join("; ");
}

export function OpenFinanceContent() {
  const toast = useToast();
  const [status, setStatus] = useState<OpenFinanceStatus | null>(null);
  const [items, setItems] = useState<OpenFinanceItem[]>([]);
  const [runs, setRuns] = useState<OpenFinanceSyncRun[]>([]);
  const [externalItemId, setExternalItemId] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [connectToken, setConnectToken] = useState<string | null>(null);
  const [connectUpdateItemId, setConnectUpdateItemId] = useState<string | null>(null);

  const lastRun = runs[0] ?? null;
  const totals = useMemo(() => {
    return runs.reduce(
      (summary, run) => {
        summary.created += run.transactions_created;
        summary.updated += run.transactions_updated;
        summary.ignored += run.transactions_ignored;
        return summary;
      },
      { created: 0, updated: 0, ignored: 0 }
    );
  }, [runs]);

  async function loadData() {
    const nextStatus = await getOpenFinanceStatus();
    setStatus(nextStatus);
    if (nextStatus.enabled) {
      const [nextItems, nextRuns] = await Promise.all([getOpenFinanceItems(), getOpenFinanceSyncRuns()]);
      setItems(nextItems);
      setRuns(nextRuns);
    }
  }

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      loadData()
        .catch((err) => {
          if (active) toast.error(err instanceof Error ? err.message : "Falha ao carregar Open Finance.");
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [toast]);

  async function handleCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = externalItemId.trim();
    if (!value) return;
    try {
      setSyncing("create");
      await createOpenFinanceItem(value);
      setExternalItemId("");
      await loadData();
      toast.success("Conexao Open Finance adicionada.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao adicionar conexao.");
    } finally {
      setSyncing(null);
    }
  }

  async function handleConnect() {
    try {
      setSyncing("connect");
      const token = await createOpenFinanceConnectToken();
      setConnectUpdateItemId(null);
      setConnectToken(token.connect_token);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao iniciar conexao Open Finance.");
    } finally {
      setSyncing(null);
    }
  }

  async function handleReconnect(item: OpenFinanceItem) {
    try {
      setSyncing(`reconnect-${item.external_item_id}`);
      const token = await createOpenFinanceConnectToken();
      setConnectUpdateItemId(item.external_item_id);
      setConnectToken(token.connect_token);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao iniciar reconexao Open Finance.");
    } finally {
      setSyncing(null);
    }
  }

  async function handleConnectSuccess(data: { item?: { id?: string | number } }) {
    const itemId = data.item?.id ? String(data.item.id) : connectUpdateItemId ?? "";
    if (!itemId) {
      toast.error("Conexao criada, mas a Pluggy nao retornou o item.");
      return;
    }
    try {
      setSyncing(itemId);
      await createOpenFinanceItem(itemId);
      await syncOpenFinanceItem(itemId);
      await loadData();
      toast.success("Conexao Open Finance criada e sincronizada.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar conexao Open Finance.");
    } finally {
      setConnectToken(null);
      setConnectUpdateItemId(null);
      setSyncing(null);
    }
  }

  async function handleSyncAll() {
    try {
      setSyncing("all");
      await syncOpenFinance();
      await loadData();
      toast.success("Sincronizacao Open Finance concluida.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao sincronizar Open Finance.");
    } finally {
      setSyncing(null);
    }
  }

  async function handleSyncItem(item: OpenFinanceItem) {
    try {
      setSyncing(item.external_item_id);
      await syncOpenFinanceItem(item.external_item_id);
      await loadData();
      toast.success("Conexao sincronizada.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao sincronizar conexao.");
    } finally {
      setSyncing(null);
    }
  }

  if (loading) {
    return <div className="rounded-lg border border-stone-200 bg-white p-6 text-sm text-stone-500 shadow-sm">Carregando Open Finance...</div>;
  }

  if (!status?.enabled) {
    return (
      <section className="grid gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Open Finance</h1>
          <p className="mt-1 text-sm text-stone-500">Indisponivel para esta sessao.</p>
        </div>
        <div className="flex items-center gap-3 rounded-lg border border-stone-200 bg-white p-5 text-sm text-stone-600 shadow-sm">
          <AlertCircle className="h-5 w-5 text-stone-500" />
          <span>Feature desabilitada ou restrita ao owner.</span>
        </div>
      </section>
    );
  }

  return (
    <section className="grid gap-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Open Finance</h1>
          <p className="mt-1 text-sm text-stone-500">Pluggy owner-only</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <UiButton disabled={Boolean(syncing) || Boolean(connectToken) || !status.configured} onClick={handleConnect} type="button">
            <ShieldCheck className="h-4 w-4" />
            Conectar banco
          </UiButton>
          <UiButton disabled={Boolean(syncing) || !status.configured} onClick={handleSyncAll} type="button" variant="secondary">
            <RefreshCw className={cn("h-4 w-4", syncing === "all" && "animate-spin")} />
            Sincronizar tudo
          </UiButton>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase text-stone-500">Conexoes</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{items.length}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase text-stone-500">Ultima sync</p>
          <p className="mt-2 text-sm font-semibold text-ink">{formatDateTime(lastRun?.finished_at ?? null)}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase text-stone-500">Transacoes novas</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{totals.created}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase text-stone-500">Atualizadas</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{totals.updated}</p>
        </div>
      </div>

      {!status.configured ? (
        <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertCircle className="h-5 w-5" />
          <span>Credenciais Pluggy pendentes no backend.</span>
        </div>
      ) : null}

      <details className="rounded-lg border border-stone-200 bg-white p-4 text-sm shadow-sm">
        <summary className="cursor-pointer font-medium text-stone-700">Adicionar item manualmente</summary>
        <form className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]" onSubmit={handleCreateItem}>
          <label className="grid gap-1 text-sm">
            <span className="font-medium text-stone-700">Item ID Pluggy</span>
            <input
              className="h-10 rounded-md border border-stone-200 px-3 text-sm outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/20"
              disabled={Boolean(syncing) || !status.configured}
              onChange={(event) => setExternalItemId(event.target.value)}
              placeholder="item_xxxxx"
              value={externalItemId}
            />
          </label>
          <UiButton className="self-end" disabled={Boolean(syncing) || !status.configured || !externalItemId.trim()} type="submit" variant="secondary">
            <Plus className="h-4 w-4" />
            Adicionar
          </UiButton>
        </form>
      </details>

      {connectToken ? (
        <PluggyConnect
          connectToken={connectToken}
          language="pt"
          onClose={() => {
            setConnectToken(null);
            setConnectUpdateItemId(null);
          }}
          onError={(error) => {
            setConnectToken(null);
            setConnectUpdateItemId(null);
            toast.error(error.message || "Falha na conexao Pluggy.");
          }}
          onLoadError={(error) => {
            setConnectToken(null);
            setConnectUpdateItemId(null);
            toast.error(error.message || "Falha ao carregar Pluggy Connect.");
          }}
          products={OPEN_FINANCE_PRODUCTS}
          updateItem={connectUpdateItemId ?? undefined}
          forceAskForCredentials={Boolean(connectUpdateItemId)}
          onSuccess={handleConnectSuccess}
        />
      ) : null}

      <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-stone-100 px-4 py-3">
          <Landmark className="h-4 w-4 text-mint" />
          <h2 className="text-sm font-semibold text-ink">Conexoes</h2>
        </div>
        {items.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-stone-500">Nenhuma conexao cadastrada.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-4 py-3">Instituicao</th>
                  <th className="px-4 py-3">Item</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Ultima sync</th>
                  <th className="px-4 py-3 text-right">Acao</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-t border-stone-100">
                    <td className="px-4 py-3 font-medium text-ink">{item.institution_name || item.connector_name || "Open Finance"}</td>
                    <td className="px-4 py-3 text-stone-500">{item.external_item_id}</td>
                    <td className="px-4 py-3">
                      <span className={cn("inline-flex rounded-full px-2 py-1 text-xs font-medium ring-1", statusClass(item.status))}>{item.status}</span>
                    </td>
                    <td className="px-4 py-3 text-stone-500">{formatDateTime(item.last_successful_sync_at || item.last_sync_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <UiButton disabled={Boolean(syncing) || Boolean(connectToken) || !status.configured} onClick={() => handleReconnect(item)} size="sm" type="button" variant="secondary">
                          <ShieldCheck className="h-4 w-4" />
                          Reconectar
                        </UiButton>
                        <UiButton disabled={Boolean(syncing) || !status.configured} onClick={() => handleSyncItem(item)} size="sm" type="button" variant="secondary">
                          <RefreshCw className={cn("h-4 w-4", syncing === item.external_item_id && "animate-spin")} />
                          Sincronizar
                        </UiButton>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-stone-100 px-4 py-3">
          <Activity className="h-4 w-4 text-mint" />
          <h2 className="text-sm font-semibold text-ink">Historico de sync</h2>
        </div>
        {runs.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-stone-500">Nenhuma sincronizacao executada.</div>
        ) : (
          <div className="divide-y divide-stone-100">
            {runs.map((run) => (
              <div key={run.id} className="grid gap-3 px-4 py-3 md:grid-cols-[1fr_auto] md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("inline-flex rounded-full px-2 py-1 text-xs font-medium ring-1", statusClass(run.status))}>
                      {run.status === "success" ? <CheckCircle2 className="mr-1 h-3 w-3" /> : null}
                      {run.status}
                    </span>
                    <span className="text-sm font-medium text-ink">{run.external_item_id || "Todos os items"}</span>
                    <span className="text-xs text-stone-500">{formatDateTime(run.started_at)}</span>
                  </div>
                  {run.error_message ? <p className="mt-1 text-sm text-red-600">{run.error_message}</p> : null}
                </div>
                <div className="text-sm text-stone-600">
                  <div>
                    {run.transactions_created} novas, {run.transactions_updated} atualizadas, {run.transactions_ignored} ignoradas
                  </div>
                  <div className="mt-1 text-xs text-stone-500">
                    Pluggy: {run.metadata.accounts_found ?? 0} contas, {run.metadata.transactions_found ?? 0} transacoes
                    {run.metadata.item_execution_status ? `, execucao ${run.metadata.item_execution_status}` : ""}
                  </div>
                  {formatIgnoredReasons(run.metadata.transactions_ignored_reasons) ? (
                    <div className="mt-1 text-xs text-stone-500">Ignoradas: {formatIgnoredReasons(run.metadata.transactions_ignored_reasons)}</div>
                  ) : null}
                  {formatAccountErrors(run.metadata.transaction_account_errors) ? (
                    <div className="mt-1 max-w-xl truncate text-xs text-red-600" title={run.metadata.transaction_account_errors?.map((error) => error.message).join("\n")}>
                      Erros: {formatAccountErrors(run.metadata.transaction_account_errors)}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
