import type { Metadata } from "next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { Analytics } from "@vercel/analytics/next";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/components/auth-provider";
import { ThemeInitializer } from "@/components/theme-initializer";
import { ToastProvider } from "@/components/toast-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Financy",
  description: "Gerenciamento financeiro para contas, cartoes, transacoes e importacoes",
  icons: {
    icon: "/brand/financy-icon.png",
    shortcut: "/brand/financy-icon.png",
    apple: "/brand/financy-icon.png"
  }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" data-theme="light" data-density="comfortable" data-reduce-motion="false" suppressHydrationWarning>
      <body>
        <ThemeInitializer />
        <AuthProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </AuthProvider>
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  );
}
