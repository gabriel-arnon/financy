import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/components/auth-provider";
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

const themeInitScript = `
try {
  var raw = window.localStorage.getItem("financy_user_preferences");
  var preferences = raw ? JSON.parse(raw) : {};
  var theme = preferences.theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.density = preferences.density === "compact" ? "compact" : "comfortable";
  document.documentElement.dataset.reduceMotion = preferences.reduceMotion ? "true" : "false";
} catch (error) {
  document.documentElement.dataset.theme = "light";
}
`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <AuthProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
