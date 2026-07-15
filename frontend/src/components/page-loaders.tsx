"use client";

import { ReactNode, useCallback, useEffect, useState } from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { AccountsContent } from "@/components/accounts-content";
import { CardsContent } from "@/components/cards-content";
import { DashboardContent } from "@/components/dashboard-content";
import { GuestReimbursementsContent } from "@/components/guest-reimbursements-content";
import { ReimbursementsContent } from "@/components/reimbursements-content";
import { RulesContent } from "@/components/rules-content";
import { StatementsContent } from "@/components/statements-content";
import { TransactionsTable } from "@/components/transactions-table";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast-provider";
import { UiButton } from "@/components/ui-button";
import {
  getAccounts,
  getCards,
  getCategories,
  getClassificationRules,
  getReimbursementClaims,
  getReimbursementContacts,
  getReimbursementEligibleTransactions,
  getReimbursementOverview,
  getReimbursementInvitations,
  getReimbursementMemberships,
  getGuestReimbursementClaims,
  getStatements,
  getTransactions
} from "@/lib/api";
import type { Account, Card, CardStatementSummary, Category, ClassificationRule, Transaction, TransactionType } from "@/lib/types";

type LoaderVariant = "dashboard" | "list" | "transactions" | "cards" | "rules";

interface PageLoadingStateProps {
  label?: string;
  variant?: LoaderVariant;
}

interface PageErrorStateProps {
  message: string;
  onRetry: () => void;
}

function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-stone-100 ${className}`} />;
}

function PageHeaderSkeleton({ metric = false }: { metric?: boolean }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-3">
        <SkeletonBlock className="h-4 w-24" />
        <SkeletonBlock className="h-8 w-72 max-w-full" />
        <SkeletonBlock className="h-4 w-96 max-w-full" />
      </div>
      {metric ? <SkeletonBlock className="h-10 w-32" /> : null}
    </div>
  );
}

function SummaryCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <SkeletonBlock className="h-3 w-24" />
          <SkeletonBlock className="mt-4 h-7 w-32" />
          <SkeletonBlock className="mt-3 h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

function TableSkeleton({ rows = 7, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
      <div className="grid gap-3 border-b border-stone-100 bg-stone-50 px-4 py-3" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {Array.from({ length: columns }).map((_, index) => (
          <SkeletonBlock key={index} className="h-3 w-20" />
        ))}
      </div>
      <div className="divide-y divide-stone-100">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="grid gap-3 px-4 py-4" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
            {Array.from({ length: columns }).map((_, columnIndex) => (
              <SkeletonBlock key={columnIndex} className={columnIndex === 1 ? "h-4 w-full" : "h-4 w-24"} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function ListCardsSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <SkeletonBlock className="h-5 w-44" />
          <SkeletonBlock className="mt-4 h-4 w-28" />
          <SkeletonBlock className="mt-6 h-10 w-full" />
        </div>
      ))}
    </div>
  );
}

function LoadingBody({ variant }: { variant: LoaderVariant }) {
  if (variant === "dashboard") {
    return (
      <>
        <SummaryCardsSkeleton />
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <TableSkeleton rows={5} columns={4} />
          <ListCardsSkeleton rows={3} />
        </div>
      </>
    );
  }

  if (variant === "transactions") {
    return (
      <>
        <SummaryCardsSkeleton />
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <div className="grid gap-3 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <SkeletonBlock key={index} className="h-10 w-full" />
            ))}
          </div>
        </div>
        <TableSkeleton rows={8} columns={6} />
      </>
    );
  }

  if (variant === "cards") {
    return (
      <>
        <SummaryCardsSkeleton count={3} />
        <ListCardsSkeleton rows={4} />
      </>
    );
  }

  if (variant === "rules") {
    return (
      <>
        <div className="rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
          <div className="grid gap-3 lg:grid-cols-[1.4fr_1.2fr_1fr_1fr_0.7fr]">
            {Array.from({ length: 5 }).map((_, index) => (
              <SkeletonBlock key={index} className="h-10 w-full" />
            ))}
          </div>
        </div>
        <TableSkeleton rows={5} columns={5} />
      </>
    );
  }

  return <ListCardsSkeleton rows={5} />;
}

function LoadingState({ label = "Carregando...", variant = "list" }: PageLoadingStateProps) {
  return (
    <section className="relative min-h-[65vh] space-y-6" aria-busy="true" aria-live="polite">
      <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
        <div className="flex w-full max-w-xs items-center justify-center gap-3 rounded-lg border border-stone-200 bg-white px-5 py-4 text-sm font-medium text-stone-600 shadow-sm">
          <Loader2 className="h-4 w-4 animate-spin text-mint" />
          <span>{label || "Carregando..."}</span>
        </div>
      </div>
      <div className="space-y-6 opacity-70">
        <PageHeaderSkeleton metric={variant === "transactions"} />
        <LoadingBody variant={variant} />
      </div>
    </section>
  );
}

function ErrorState({ message, onRetry }: PageErrorStateProps) {
  return (
    <section className="rounded-lg border border-red-100 bg-white p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 text-red-500" />
        <div className="min-w-0">
          <h1 className="text-lg font-semibold text-ink">Nao foi possivel carregar os dados.</h1>
          <p className="mt-2 text-sm leading-6 text-stone-600">{message}</p>
          <UiButton className="mt-4" icon={<RefreshCw className="h-4 w-4" />} onClick={onRetry} variant="secondary">
            Tentar novamente
          </UiButton>
        </div>
      </div>
    </section>
  );
}

function useReadyForData() {
  const { configured, loading, session } = useAuth();
  return !configured || (!loading && Boolean(session));
}

function getErrorMessage(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

function usePageData<T>(ready: boolean, load: () => Promise<T>, fallbackError: string) {
  const toast = useToast();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!ready) return;
    setLoading(true);
    setError(null);
    load()
      .then(setData)
      .catch((err) => {
        const message = getErrorMessage(err, fallbackError);
        setError(message);
        toast.error(message);
      })
      .finally(() => setLoading(false));
  }, [fallbackError, load, ready, toast]);

  useEffect(() => {
    const timeoutId = window.setTimeout(reload, 0);
    return () => window.clearTimeout(timeoutId);
  }, [reload]);

  return { data, loading, error, reload };
}

function PageDataBoundary<T>({
  data,
  error,
  label,
  loading,
  reload,
  render,
  variant,
}: {
  data: T | null;
  error: string | null;
  label: string;
  loading: boolean;
  reload: () => void;
  render: (data: T) => ReactNode;
  variant: LoaderVariant;
}) {
  if (loading) return <LoadingState label={label} variant={variant} />;
  if (error || data === null) return <ErrorState message={error ?? "Tente novamente em alguns segundos."} onRetry={reload} />;
  return <>{render(data)}</>;
}

export function DashboardPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [transactions, categories, accounts, cards] = await Promise.all([getTransactions(), getCategories(), getAccounts(), getCards()]);
    return { transactions, categories, accounts, cards };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar dashboard.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando dashboard..."
      variant="dashboard"
      render={({ transactions, categories, accounts, cards }) => (
        <DashboardContent transactions={transactions} categories={categories} accounts={accounts} cards={cards} />
      )}
    />
  );
}

export function AccountsPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [accounts, cards] = await Promise.all([getAccounts(), getCards()]);
    return { accounts, cards };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar contas.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando contas..."
      variant="list"
      render={({ accounts, cards }) => <AccountsContent initialAccounts={accounts} initialCards={cards} />}
    />
  );
}

export function CardsPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [accounts, cards, statements] = await Promise.all([getAccounts(), getCards(), getStatements()]);
    return { accounts, cards, statements };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar cartoes.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando cartoes..."
      variant="cards"
      render={({ accounts, cards, statements }) => (
        <CardsContent initialAccounts={accounts} initialCards={cards} initialStatements={statements} />
      )}
    />
  );
}

export function TransactionsPageLoader({
  initialCardId,
  initialCardStatementId,
  initialCreateType,
  initialFilters,
}: {
  initialCardId: string | null;
  initialCardStatementId: string | null;
  initialCreateType?: TransactionType | null;
  initialFilters?: {
    categoryId?: string | null;
    cleanup?: string | null;
    endDate?: string | null;
    query?: string | null;
    source?: string | null;
    startDate?: string | null;
    status?: string | null;
    transactionIds?: string | null;
    type?: string | null;
  };
}) {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [transactions, categories, accounts, cards] = await Promise.all([getTransactions(), getCategories(), getAccounts(), getCards()]);
    return { transactions, categories, accounts, cards };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar transacoes.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando transacoes..."
      variant="transactions"
      render={({ transactions, categories, accounts, cards }) => (
        <section className="space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-mint">Transacoes</p>
              <h1 className="mt-2 text-3xl font-semibold text-ink">Lancamentos confirmados</h1>
              <p className="mt-2 text-sm text-stone-500">Filtre por periodo, tipo, categoria, conta, cartao ou descricao.</p>
            </div>
            <p className="rounded-md bg-white px-3 py-2 text-sm text-stone-600 shadow-sm">{transactions.length} transacoes</p>
          </div>
          <TransactionsTable
            transactions={transactions}
            categories={categories}
            accounts={accounts}
            cards={cards}
            initialCardId={initialCardId}
            initialCardStatementId={initialCardStatementId}
            initialCreateType={initialCreateType}
            initialFilters={initialFilters}
          />
        </section>
      )}
    />
  );
}

export function StatementsPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [statements, accounts, cards] = await Promise.all([getStatements(), getAccounts(), getCards()]);
    return { statements, accounts, cards };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar faturas.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando faturas..."
      variant="list"
      render={({ statements, accounts, cards }) => <StatementsContent accounts={accounts} cards={cards} statements={statements} />}
    />
  );
}

export function ReimbursementsPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [overview, contacts, claims, eligibleTransactions, categories, accounts, cards, invitations, memberships] = await Promise.all([
      getReimbursementOverview(),
      getReimbursementContacts(),
      getReimbursementClaims(),
      getReimbursementEligibleTransactions({ limit: 50 }),
      getCategories(),
      getAccounts(),
      getCards(),
      getReimbursementInvitations(),
      getReimbursementMemberships()
    ]);
    return { overview, contacts, claims, eligibleTransactions, categories, accounts, cards, invitations, memberships };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar ressarcimentos.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando ressarcimentos..."
      variant="list"
      render={({ overview, contacts, claims, eligibleTransactions, categories, accounts, cards, invitations, memberships }) => (
        <ReimbursementsContent
          initialAccounts={accounts}
          initialCards={cards}
          initialCategories={categories}
          initialClaims={claims}
          initialContacts={contacts}
          initialEligibleTransactions={eligibleTransactions}
          initialInvitations={invitations}
          initialMemberships={memberships}
          initialOverview={overview}
        />
      )}
    />
  );
}

export function GuestReimbursementsPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const claims = await getGuestReimbursementClaims();
    return { claims };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar portal de ressarcimentos.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando portal..."
      variant="list"
      render={({ claims }) => <GuestReimbursementsContent initialClaims={claims} />}
    />
  );
}

export function RulesPageLoader() {
  const ready = useReadyForData();
  const load = useCallback(async () => {
    const [rules, categories] = await Promise.all([getClassificationRules(), getCategories()]);
    return { rules, categories };
  }, []);
  const state = usePageData(ready, load, "Falha ao carregar regras.");

  return (
    <PageDataBoundary
      {...state}
      label="Carregando regras..."
      variant="rules"
      render={({ rules, categories }) => <RulesContent initialRules={rules} initialCategories={categories} skipInitialLoad />}
    />
  );
}
