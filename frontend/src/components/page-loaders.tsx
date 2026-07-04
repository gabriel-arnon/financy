"use client";

import { useEffect, useState } from "react";
import { AccountsContent } from "@/components/accounts-content";
import { CardsContent } from "@/components/cards-content";
import { DashboardContent } from "@/components/dashboard-content";
import { RulesContent } from "@/components/rules-content";
import { StatementsContent } from "@/components/statements-content";
import { TransactionsTable } from "@/components/transactions-table";
import { useAuth } from "@/components/auth-provider";
import {
  getAccounts,
  getCards,
  getCategories,
  getClassificationRules,
  getStatements,
  getTransactions
} from "@/lib/api";
import type { Account, Card, CardStatementSummary, Category, ClassificationRule, Transaction } from "@/lib/types";

function LoadingState({ label = "Carregando dados..." }: { label?: string }) {
  return <p className="rounded-lg border border-stone-200 bg-white px-4 py-8 text-center text-sm text-stone-500 shadow-sm">{label}</p>;
}

function useReadyForData() {
  const { configured, loading, session } = useAuth();
  return !configured || (!loading && Boolean(session));
}

export function DashboardPageLoader() {
  const ready = useReadyForData();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([getTransactions(), getCategories(), getAccounts(), getCards()])
      .then(([nextTransactions, nextCategories, nextAccounts, nextCards]) => {
        setTransactions(nextTransactions);
        setCategories(nextCategories);
        setAccounts(nextAccounts);
        setCards(nextCards);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) return <LoadingState label="Carregando dashboard..." />;
  return <DashboardContent transactions={transactions} categories={categories} accounts={accounts} cards={cards} />;
}

export function AccountsPageLoader() {
  const ready = useReadyForData();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([getAccounts(), getCards()])
      .then(([nextAccounts, nextCards]) => {
        setAccounts(nextAccounts);
        setCards(nextCards);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) return <LoadingState label="Carregando contas..." />;
  return <AccountsContent initialAccounts={accounts} initialCards={cards} />;
}

export function CardsPageLoader() {
  const ready = useReadyForData();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [statements, setStatements] = useState<CardStatementSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([getAccounts(), getCards(), getStatements()])
      .then(([nextAccounts, nextCards, nextStatements]) => {
        setAccounts(nextAccounts);
        setCards(nextCards);
        setStatements(nextStatements);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) return <LoadingState label="Carregando cartoes..." />;
  return <CardsContent initialAccounts={accounts} initialCards={cards} initialStatements={statements} />;
}

export function TransactionsPageLoader({ initialCardId, initialCardStatementId }: { initialCardId: string | null; initialCardStatementId: string | null }) {
  const ready = useReadyForData();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([getTransactions(), getCategories(), getAccounts(), getCards()])
      .then(([nextTransactions, nextCategories, nextAccounts, nextCards]) => {
        setTransactions(nextTransactions);
        setCategories(nextCategories);
        setAccounts(nextAccounts);
        setCards(nextCards);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) return <LoadingState label="Carregando transacoes..." />;
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-mint">Transacoes</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Lancamentos confirmados</h1>
          <p className="mt-2 text-sm text-stone-500">Filtre por periodo, tipo, categoria, conta, cartao ou descricao.</p>
        </div>
        <p className="rounded-md bg-white px-3 py-2 text-sm text-stone-600 shadow-sm">{transactions.length} transacoes</p>
      </div>
      <TransactionsTable transactions={transactions} categories={categories} accounts={accounts} cards={cards} initialCardId={initialCardId} initialCardStatementId={initialCardStatementId} />
    </section>
  );
}

export function StatementsPageLoader() {
  const ready = useReadyForData();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [statements, setStatements] = useState<CardStatementSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([getStatements(), getAccounts(), getCards()])
      .then(([nextStatements, nextAccounts, nextCards]) => {
        setStatements(nextStatements);
        setAccounts(nextAccounts);
        setCards(nextCards);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) return <LoadingState label="Carregando faturas..." />;
  return <StatementsContent accounts={accounts} cards={cards} statements={statements} />;
}

export function RulesPageLoader() {
  const ready = useReadyForData();
  const [rules, setRules] = useState<ClassificationRule[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    Promise.all([getClassificationRules(), getCategories()])
      .then(([nextRules, nextCategories]) => {
        setRules(nextRules);
        setCategories(nextCategories);
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (loading) return <LoadingState label="Carregando regras..." />;
  return <RulesContent initialRules={rules} initialCategories={categories} />;
}
