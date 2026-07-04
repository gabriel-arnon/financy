"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { CreditCard, Landmark, Plus } from "lucide-react";
import { ImportPreviewTable } from "@/components/import-preview-table";
import { UiButton } from "@/components/ui-button";
import { createAccount, createCard, getAccounts, getCards, getImportPreview, updateCard } from "@/lib/api";
import { formatAccountName, isActiveEntity } from "@/lib/labels";
import type { Account, AccountPayload, AccountType, Card, CardPayload, ImportPreviewItem, ImportPreviewResponse } from "@/lib/types";

interface DetectedCard {
  lastDigits: string;
  name: string;
  brand: string | null;
  institution: string | null;
  limitAmount: string | null;
  dueDate: string | null;
}

interface DetectedAccount {
  institution: string | null;
  agency: string | null;
  accountNumber: string | null;
  balance: string | null;
}

const emptyAccountForm: AccountPayload = {
  name: "",
  institution: "",
  agency: null,
  account_number: null,
  type: "checking",
  balance: "0",
  status: "active"
};

function detectedCardFromItems(items: ImportPreviewItem[]): DetectedCard | null {
  const item = items.find((previewItem) => previewItem.card_last_digits);
  if (!item?.card_last_digits) return null;
  return {
    lastDigits: item.card_last_digits,
    name: item.card_name || (item.card_brand ? `Cartão ${item.card_brand}` : `Cartão final ${item.card_last_digits}`),
    brand: item.card_brand,
    institution: item.card_institution,
    limitAmount: item.card_limit_amount,
    dueDate: item.statement_due_date
  };
}

function detectedAccountFromItems(items: ImportPreviewItem[]): DetectedAccount | null {
  const item = items.find((previewItem) => previewItem.account_agency || previewItem.account_number);
  if (!item?.account_agency && !item?.account_number) return null;
  return {
    institution: item.account_institution,
    agency: item.account_agency,
    accountNumber: item.account_number,
    balance: item.account_balance
  };
}

function normalize(value: string | null | undefined) {
  return (value ?? "").trim().toUpperCase();
}

function sameDetectedAccount(account: Account, detected: DetectedAccount) {
  if (detected.agency && detected.accountNumber) {
    return account.agency === detected.agency && account.account_number === detected.accountNumber;
  }
  if (detected.accountNumber) return account.account_number === detected.accountNumber;
  return false;
}

export function ImportPreviewPanel({ importId }: { importId: string }) {
  const [data, setData] = useState<ImportPreviewResponse | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [creatingCard, setCreatingCard] = useState(false);
  const [creatingAccount, setCreatingAccount] = useState(false);
  const [accountForm, setAccountForm] = useState<AccountPayload>(emptyAccountForm);
  const [modalStep, setModalStep] = useState<"card" | "account">("card");
  const [error, setError] = useState<{ importId: string; message: string } | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const updatedExistingCardIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    let active = true;
    Promise.all([getImportPreview(importId), getAccounts(), getCards()])
      .then(([response, nextAccounts, nextCards]) => {
        if (!active) return;
        const activeAccounts = nextAccounts.filter(isActiveEntity);
        setData(response);
        setAccounts(activeAccounts);
        setCards(nextCards.filter(isActiveEntity));
        setSelectedAccountId(activeAccounts[0]?.id ?? "");
        setAccountForm(emptyAccountForm);
        setModalStep("card");
        updatedExistingCardIds.current.clear();
        setSuggestionError(null);
      })
      .catch((err) => {
        if (active) setError({ importId, message: err instanceof Error ? err.message : "Falha ao carregar prévia" });
      });
    return () => {
      active = false;
    };
  }, [importId]);

  const detectedCard = useMemo(() => detectedCardFromItems(data?.items ?? []), [data?.items]);
  const detectedAccount = useMemo(() => detectedAccountFromItems(data?.items ?? []), [data?.items]);
  const existingAccount = useMemo(() => {
    if (!detectedAccount) return undefined;
    return accounts.find((account) => sameDetectedAccount(account, detectedAccount));
  }, [accounts, detectedAccount]);
  const existingCard = useMemo(() => {
    if (!detectedCard) return undefined;
    return cards.find((card) => {
      if (card.last_digits !== detectedCard.lastDigits) return false;
      if (detectedCard.brand && card.brand && normalize(card.brand) !== normalize(detectedCard.brand)) return false;
      if (detectedCard.institution && card.institution && normalize(card.institution) !== normalize(detectedCard.institution)) return false;
      return true;
    });
  }, [cards, detectedCard]);
  const mustResolveDetectedAccount = Boolean(detectedAccount && !existingAccount);
  const mustResolveDetectedCard = Boolean(detectedCard && !existingCard);
  const effectiveModalStep = mustResolveDetectedAccount ? "account" : modalStep;

  useEffect(() => {
    if (!detectedCard || !existingCard || updatedExistingCardIds.current.has(existingCard.id)) return;
    const patch: Partial<CardPayload> = {};
    if (detectedCard.limitAmount && !existingCard.limit_amount) patch.limit_amount = detectedCard.limitAmount;
    if (detectedCard.institution && !existingCard.institution) patch.institution = detectedCard.institution;
    if (detectedCard.brand && !existingCard.brand) patch.brand = detectedCard.brand;
    if (detectedCard.name && existingCard.name.startsWith("Cartão final")) patch.name = detectedCard.name;
    if (detectedCard.dueDate && !existingCard.due_day) patch.due_day = Number(detectedCard.dueDate.slice(8, 10));
    if (Object.keys(patch).length === 0) return;

    updatedExistingCardIds.current.add(existingCard.id);
    updateCard(existingCard.id, patch)
      .then((updated) => {
        setCards((current) => current.map((card) => (card.id === updated.id ? updated : card)));
      })
      .catch(() => {
        updatedExistingCardIds.current.delete(existingCard.id);
      });
  }, [detectedCard, existingCard]);

  async function handleCreateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingAccount(true);
    setSuggestionError(null);
    try {
      const created = await createAccount({
        ...accountForm,
        institution: accountForm.institution || null,
        agency: accountForm.agency || null,
        account_number: accountForm.account_number || null,
        balance: accountForm.balance || "0",
        status: "active"
      });
      setAccounts((current) => [...current.filter((account) => account.id !== created.id), created]);
      setSelectedAccountId(created.id);
      setAccountForm(emptyAccountForm);
      setModalStep("card");
    } catch (err) {
      setSuggestionError(err instanceof Error ? err.message : "Falha ao criar conta bancária.");
    } finally {
      setCreatingAccount(false);
    }
  }

  async function handleCreateDetectedAccount() {
    if (!detectedAccount) return;
    setCreatingAccount(true);
    setSuggestionError(null);
    try {
      const created = await createAccount({
        name: detectedAccount.institution || "Conta bancária",
        institution: detectedAccount.institution,
        agency: detectedAccount.agency,
        account_number: detectedAccount.accountNumber,
        type: "checking",
        balance: detectedAccount.balance || "0",
        status: "active"
      });
      setAccounts((current) => [...current.filter((account) => account.id !== created.id), created]);
      setSelectedAccountId(created.id);
      setModalStep(mustResolveDetectedCard ? "card" : "account");
    } catch (err) {
      setSuggestionError(err instanceof Error ? err.message : "Falha ao criar conta bancária.");
    } finally {
      setCreatingAccount(false);
    }
  }

  async function handleCreateDetectedCard() {
    if (!detectedCard) return;
    if (!selectedAccountId) {
      setSuggestionError("Crie ou selecione uma conta bancária para vincular o cartão.");
      setModalStep("account");
      return;
    }
    setCreatingCard(true);
    setSuggestionError(null);
    try {
      const payload: CardPayload = {
        account_id: selectedAccountId,
        name: detectedCard.name,
        institution: detectedCard.institution,
        brand: detectedCard.brand,
        last_digits: detectedCard.lastDigits,
        limit_amount: detectedCard.limitAmount,
        closing_day: null,
        due_day: detectedCard.dueDate ? Number(detectedCard.dueDate.slice(8, 10)) : null,
        status: "active"
      };
      const created = await createCard(payload);
      setCards((current) => [...current.filter((card) => card.id !== created.id), created]);
    } catch (err) {
      setSuggestionError(err instanceof Error ? err.message : "Falha ao criar cartão.");
    } finally {
      setCreatingCard(false);
    }
  }

  if (error?.importId === importId) return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error.message}</p>;
  if (!data || data.import_id !== importId) return <p className="text-sm text-stone-500">Carregando prévia...</p>;

  return (
    <>
      <ImportPreviewTable
        key={`${importId}:${accounts.map((account) => account.id).join(",")}:${cards.map((card) => card.id).join(",")}`}
        importId={importId}
        items={data.items}
        categories={data.categories}
        accounts={accounts}
        cards={cards}
      />

      {mustResolveDetectedAccount || mustResolveDetectedCard ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-lg border border-stone-200 bg-white shadow-2xl">
            <div className="border-b border-stone-200 px-5 py-4">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
                {effectiveModalStep === "account" ? <Landmark className="h-5 w-5 text-mint" /> : <CreditCard className="h-5 w-5 text-mint" />}
                {effectiveModalStep === "account" && mustResolveDetectedAccount ? "Conta bancária detectada no extrato" : effectiveModalStep === "account" ? "Criar conta bancária" : "Cartão detectado na fatura"}
              </h2>
              <p className="mt-1 text-sm text-stone-500">
                {effectiveModalStep === "account" && mustResolveDetectedAccount
                  ? "Não encontramos uma conta bancária ativa com esses dados. Confirme a criação para vincular os lançamentos."
                  : "Para confirmar a importação desta fatura, vincule os lançamentos a um cartão de crédito."}
              </p>
            </div>

            {effectiveModalStep === "account" && mustResolveDetectedAccount && detectedAccount ? (
              <>
                <div className="space-y-4 px-5 py-5">
                  <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    Nenhuma conta bancária correspondente foi encontrada. O Financy pode criar uma conta com os dados abaixo.
                  </div>
                  <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
                    <p className="font-medium text-ink">{detectedAccount.institution ?? "Instituição não detectada"}</p>
                    <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs font-medium uppercase text-stone-500">Agência</dt>
                        <dd className="mt-1 text-sm font-semibold text-ink">{detectedAccount.agency ?? "Não detectada"}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium uppercase text-stone-500">Conta</dt>
                        <dd className="mt-1 text-sm font-semibold text-ink">{detectedAccount.accountNumber ?? "Não detectada"}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium uppercase text-stone-500">Tipo</dt>
                        <dd className="mt-1 text-sm font-semibold text-ink">Conta Corrente</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium uppercase text-stone-500">Saldo identificado</dt>
                        <dd className="mt-1 text-sm font-semibold text-ink">{detectedAccount.balance ?? "Não detectado"}</dd>
                      </div>
                    </dl>
                  </div>
                  {suggestionError ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{suggestionError}</p> : null}
                </div>
                <div className="grid gap-2 border-t border-stone-200 px-5 py-4">
                  <UiButton disabled={creatingAccount} icon={<Plus className="h-4 w-4" />} onClick={handleCreateDetectedAccount} variant="primary">
                    {creatingAccount ? "Criando..." : "Criar conta bancária e continuar"}
                  </UiButton>
                </div>
              </>
            ) : effectiveModalStep === "account" ? (
              <form onSubmit={handleCreateAccount}>
                <div className="space-y-4 px-5 py-5">
                  <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    Nenhuma conta bancária ativa foi encontrada. Crie uma conta para vincular o cartão detectado.
                  </div>
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium text-ink">Nome</span>
                    <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Nome da conta" value={accountForm.name} onChange={(event) => setAccountForm({ ...accountForm, name: event.target.value })} required />
                  </label>
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium text-ink">Instituição</span>
                    <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="Banco ou instituição" value={accountForm.institution ?? ""} onChange={(event) => setAccountForm({ ...accountForm, institution: event.target.value })} />
                  </label>
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium text-ink">Tipo de conta</span>
                    <select className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={accountForm.type} onChange={(event) => setAccountForm({ ...accountForm, type: event.target.value as AccountType })}>
                      <option value="checking">Conta Corrente</option>
                      <option value="savings">Poupança</option>
                      <option value="wallet">Carteira</option>
                      <option value="investment">Investimento</option>
                    </select>
                  </label>
                  <label className="block space-y-1.5">
                    <span className="text-sm font-medium text-ink">Saldo inicial</span>
                    <input className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" placeholder="R$ 0,00" type="number" step="0.01" value={accountForm.balance} onChange={(event) => setAccountForm({ ...accountForm, balance: event.target.value })} />
                  </label>
                  {suggestionError ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{suggestionError}</p> : null}
                </div>
                <div className="grid gap-2 border-t border-stone-200 px-5 py-4">
                  <UiButton disabled={creatingAccount} icon={<Plus className="h-4 w-4" />} type="submit" variant="primary">
                    {creatingAccount ? "Criando..." : "Criar conta e continuar"}
                  </UiButton>
                </div>
              </form>
            ) : detectedCard ? (
              <>
                <div className="space-y-4 px-5 py-5">
                  <p className="text-sm text-stone-600">
                    Identificamos dados de cartão na fatura e não encontramos um cartão ativo correspondente.
                  </p>
                  <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
                    <p className="font-medium text-ink">{detectedCard.name} ••••{detectedCard.lastDigits}</p>
                    <p className="mt-1 text-sm text-stone-500">
                      Instituição: {detectedCard.institution ?? "Não detectada"} · Bandeira: {detectedCard.brand ?? "Não detectada"}
                    </p>
                    <p className="mt-1 text-sm text-stone-500">
                      Vencimento: {detectedCard.dueDate ?? "Não detectado"} · Limite: {detectedCard.limitAmount ?? "Não detectado"}
                    </p>
                  </div>

                  {accounts.length > 0 ? (
                    <label className="block space-y-1.5">
                      <span className="text-sm font-medium text-ink">Conta vinculada obrigatória</span>
                      <select className="h-10 w-full rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint" value={selectedAccountId} onChange={(event) => setSelectedAccountId(event.target.value)}>
                        {accounts.map((account) => <option key={account.id} value={account.id}>{formatAccountName(account)}</option>)}
                      </select>
                    </label>
                  ) : null}

                  {suggestionError ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{suggestionError}</p> : null}
                </div>

                <div className="grid gap-2 border-t border-stone-200 px-5 py-4 sm:grid-cols-2">
                  <UiButton onClick={() => setModalStep("account")} variant="secondary">
                    Criar conta bancária
                  </UiButton>
                  <UiButton disabled={creatingCard || !selectedAccountId} icon={<Plus className="h-4 w-4" />} onClick={handleCreateDetectedCard} variant="primary">
                    {creatingCard ? "Criando..." : "Criar cartão"}
                  </UiButton>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
