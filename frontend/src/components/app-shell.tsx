"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, CreditCard, FileUp, LayoutDashboard, Settings, WalletCards } from "lucide-react";
import { AuthStatus } from "@/components/auth-status";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transacoes", icon: BarChart3 },
  { href: "/accounts", label: "Contas Bancarias", icon: WalletCards },
  { href: "/cards", label: "Cartoes de Credito", icon: CreditCard },
  { href: "/importacao", label: "Importacao", icon: FileUp },
  { href: "/settings", label: "Configuracoes", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login";

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-stone-200 bg-white px-5 py-6 shadow-sm md:block">
        <Link href="/" className="flex items-center gap-3">
          <Image
            src="/brand/financy-icon.png"
            alt=""
            width={40}
            height={40}
            priority
            className="h-10 w-10 rounded-lg object-cover"
          />
          <span>
            <span className="block text-xl font-semibold text-ink">Financy</span>
            <span className="block text-xs text-stone-500">Controle financeiro</span>
          </span>
        </Link>
        <nav className="mt-9 grid gap-1">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-stone-700 hover:bg-stone-100">
              <item.icon className="h-4 w-4 text-stone-500" />
              {item.label}
            </Link>
          ))}
        </nav>
        <AuthStatus />
      </aside>
      <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 px-4 py-3 backdrop-blur md:hidden">
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-ink">
            <Image
              src="/brand/financy-icon.png"
              alt=""
              width={32}
              height={32}
              priority
              className="h-8 w-8 rounded-md object-cover"
            />
            <span>Financy</span>
          </Link>
          <nav className="flex min-w-0 gap-2 overflow-x-auto text-xs text-stone-600">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} className="whitespace-nowrap rounded-md px-2 py-1 hover:bg-stone-100">
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="md:pl-64">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
