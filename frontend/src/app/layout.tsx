import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Financy",
  description: "Gerenciamento financeiro com importacao de faturas e extratos"
};

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/transactions", label: "Transações" },
  { href: "/imports", label: "Importação" }
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="min-h-screen bg-paper">
          <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-stone-200 bg-white px-5 py-6 md:block">
            <Link href="/" className="text-xl font-semibold text-ink">Financy</Link>
            <nav className="mt-8 grid gap-1">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href} className="rounded-md px-3 py-2 text-sm text-stone-700 hover:bg-stone-100">
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="md:pl-60">
            <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
