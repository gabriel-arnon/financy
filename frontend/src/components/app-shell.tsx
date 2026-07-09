"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BarChart3, ChevronLeft, ChevronRight, CreditCard, FileUp, LayoutDashboard, Menu, Settings, WalletCards, X } from "lucide-react";
import { AuthStatus } from "@/components/auth-status";
import { cn } from "@/lib/classnames";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transações", icon: BarChart3 },
  { href: "/accounts", label: "Contas Bancárias", icon: WalletCards },
  { href: "/cards", label: "Cartões de Crédito", icon: CreditCard },
  { href: "/importacao", label: "Importação", icon: FileUp },
  { href: "/settings", label: "Configurações", icon: Settings }
];

const sidebarPreferenceKey = "financy_sidebar_collapsed";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login";
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(sidebarPreferenceKey) === "true";
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  function toggleSidebar() {
    setSidebarCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem(sidebarPreferenceKey, String(next));
      return next;
    });
  }

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden border-r border-stone-200 bg-white px-5 py-6 shadow-sm transition-[width] duration-200 md:block",
          sidebarCollapsed ? "w-20" : "w-64"
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className={cn("flex min-w-0 items-center gap-3", sidebarCollapsed && "justify-center")}>
            <Image
              src="/brand/financy-icon.png"
              alt=""
              width={40}
              height={40}
              priority
              className="h-10 w-10 rounded-lg object-cover"
            />
            {!sidebarCollapsed ? (
              <span className="min-w-0">
                <span className="block truncate text-xl font-semibold text-ink">Financy</span>
                <span className="block truncate text-xs text-stone-500">Controle financeiro</span>
              </span>
            ) : null}
          </Link>
          {!sidebarCollapsed ? (
            <button
              aria-label="Esconder menu lateral"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-stone-200 bg-white text-stone-600 shadow-sm transition hover:bg-stone-50"
              onClick={toggleSidebar}
              type="button"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        {sidebarCollapsed ? (
          <button
            aria-label="Mostrar menu lateral"
            className="mt-6 inline-flex h-9 w-9 items-center justify-center rounded-full border border-stone-200 bg-white text-stone-600 shadow-sm transition hover:bg-stone-50"
            onClick={toggleSidebar}
            type="button"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : null}

        <nav className="mt-9 grid gap-1">
          {navItems.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={sidebarCollapsed ? item.label : undefined}
                aria-label={sidebarCollapsed ? item.label : undefined}
                className={cn(
                  "flex items-center rounded-md px-3 py-2.5 text-sm font-medium transition hover:bg-stone-100",
                  sidebarCollapsed ? "justify-center" : "gap-3",
                  active ? "bg-emerald-50 text-mint" : "text-stone-700"
                )}
              >
                <item.icon className={cn("h-4 w-4", active ? "text-mint" : "text-stone-500")} />
                {!sidebarCollapsed ? <span>{item.label}</span> : null}
              </Link>
            );
          })}
        </nav>
        {!sidebarCollapsed ? <AuthStatus /> : null}
      </aside>
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/90 px-4 py-3 backdrop-blur md:hidden">
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
          <button
            aria-label="Abrir menu"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-stone-200 bg-white text-stone-700 shadow-sm transition hover:bg-stone-50"
            onClick={() => setMobileMenuOpen(true)}
            type="button"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </header>

      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button className="absolute inset-0 bg-black/40" type="button" aria-label="Fechar menu" onClick={() => setMobileMenuOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-[min(20rem,85vw)] flex-col border-r border-stone-200 bg-white px-5 py-5 shadow-2xl">
            <div className="flex items-center justify-between gap-3">
              <Link href="/" className="flex min-w-0 items-center gap-3">
                <Image src="/brand/financy-icon.png" alt="" width={40} height={40} priority className="h-10 w-10 rounded-lg object-cover" />
                <span className="min-w-0">
                  <span className="block truncate text-xl font-semibold text-ink">Financy</span>
                  <span className="block truncate text-xs text-stone-500">Controle financeiro</span>
                </span>
              </Link>
              <button
                aria-label="Fechar menu"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-stone-200 bg-white text-stone-600 transition hover:bg-stone-50"
                onClick={() => setMobileMenuOpen(false)}
                type="button"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <nav className="mt-8 grid gap-1">
              {navItems.map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium transition hover:bg-stone-100",
                      active ? "bg-emerald-50 text-mint" : "text-stone-700"
                    )}
                  >
                    <item.icon className={cn("h-4 w-4", active ? "text-mint" : "text-stone-500")} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="relative mt-auto min-h-28">
              <AuthStatus />
            </div>
          </aside>
        </div>
      ) : null}

      <main className={cn("transition-[padding] duration-200", sidebarCollapsed ? "md:pl-20" : "md:pl-64")}>
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
