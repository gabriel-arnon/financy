import Link from "next/link";
import { ArrowRight, FileUp, ListChecks, WalletCards } from "lucide-react";

const cards = [
  { label: "Importar arquivo", href: "/imports", icon: FileUp },
  { label: "Revisar transações", href: "/transactions", icon: ListChecks },
  { label: "Contas e cartões", href: "/transactions", icon: WalletCards }
];

export default function DashboardPage() {
  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">MVP financeiro</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Dashboard</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <Link key={card.label} href={card.href} className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm transition hover:border-mint">
              <div className="flex items-center justify-between">
                <Icon className="h-5 w-5 text-mint" />
                <ArrowRight className="h-4 w-4 text-stone-400" />
              </div>
              <p className="mt-6 text-lg font-medium text-ink">{card.label}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
