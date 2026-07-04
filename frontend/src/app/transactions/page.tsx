import { TransactionsPageLoader } from "@/components/page-loaders";

interface TransactionsPageProps {
  searchParams?: Promise<{ card_id?: string; card_statement_id?: string }>;
}

export default async function TransactionsPage({ searchParams }: TransactionsPageProps) {
  const resolvedSearchParams = await searchParams;
  return (
    <TransactionsPageLoader
      initialCardId={resolvedSearchParams?.card_id ?? null}
      initialCardStatementId={resolvedSearchParams?.card_statement_id ?? null}
    />
  );
}
