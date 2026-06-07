import { getTransactions } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TransactionsPage() {
  const transactions = await getTransactions().catch(() => []);

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">Transações</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Lançamentos confirmados</h1>
      </div>
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="min-w-full divide-y divide-stone-200 text-sm">
          <thead className="bg-stone-50 text-left text-xs uppercase text-stone-500">
            <tr>
              <th className="px-3 py-3">Data</th>
              <th className="px-3 py-3">Descrição</th>
              <th className="px-3 py-3">Tipo</th>
              <th className="px-3 py-3 text-right">Valor</th>
              <th className="px-3 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {transactions.map((transaction) => (
              <tr key={transaction.id}>
                <td className="px-3 py-2">{transaction.transaction_date}</td>
                <td className="px-3 py-2">{transaction.description}</td>
                <td className="px-3 py-2">{transaction.type}</td>
                <td className="px-3 py-2 text-right">{transaction.amount}</td>
                <td className="px-3 py-2">{transaction.status}</td>
              </tr>
            ))}
            {transactions.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-stone-500" colSpan={5}>Nenhuma transação confirmada ainda.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
