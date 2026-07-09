import { TransactionsPageLoader } from "@/components/page-loaders";

interface TransactionsPageProps {
  searchParams?: Promise<{
    card_id?: string;
    card_statement_id?: string;
    category_id?: string;
    cleanup?: string;
    end_date?: string;
    q?: string;
    start_date?: string;
    status?: string;
    transaction_ids?: string;
    type?: string;
  }>;
}

export default async function TransactionsPage({ searchParams }: TransactionsPageProps) {
  const resolvedSearchParams = await searchParams;
  return (
    <TransactionsPageLoader
      initialCardId={resolvedSearchParams?.card_id ?? null}
      initialCardStatementId={resolvedSearchParams?.card_statement_id ?? null}
      initialFilters={{
        categoryId: resolvedSearchParams?.category_id ?? null,
        cleanup: resolvedSearchParams?.cleanup ?? null,
        endDate: resolvedSearchParams?.end_date ?? null,
        query: resolvedSearchParams?.q ?? null,
        startDate: resolvedSearchParams?.start_date ?? null,
        status: resolvedSearchParams?.status ?? null,
        transactionIds: resolvedSearchParams?.transaction_ids ?? null,
        type: resolvedSearchParams?.type ?? null,
      }}
    />
  );
}
