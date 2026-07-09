import { SlidersHorizontal } from "lucide-react";
import { RulesContent } from "@/components/rules-content";
import { SettingsCategoriesSection } from "@/components/settings-categories-section";
import { SettingsProfileAppearance } from "@/components/settings-profile-appearance";

const settingsNav = [
  { href: "#settings-profile", label: "Perfil" },
  { href: "#settings-appearance", label: "Aparência" },
  { href: "#settings-categories", label: "Categorias" },
  { href: "#settings-rules", label: "Regras" },
];

export default function SettingsPage() {
  return (
    <section className="space-y-6">
      <div className="flex items-start gap-3">
        <SlidersHorizontal className="mt-1 h-7 w-7 text-mint" />
        <div>
          <h1 className="text-3xl font-semibold text-ink">Configurações</h1>
          <p className="mt-2 text-sm font-medium text-stone-600">Configure perfil, preferências, categorias e regras.</p>
        </div>
      </div>

      <nav
        aria-label="Navegação interna de configurações"
        className="sticky top-0 z-10 overflow-x-auto rounded-lg border border-stone-200 bg-white/95 p-2 shadow-sm backdrop-blur"
      >
        <div className="flex min-w-max gap-2">
          {settingsNav.map((item) => (
            <a
              className="inline-flex h-9 items-center justify-center whitespace-nowrap rounded-md px-3 text-sm font-medium text-stone-600 transition hover:bg-emerald-50 hover:text-mint"
              href={item.href}
              key={item.href}
            >
              {item.label}
            </a>
          ))}
        </div>
      </nav>

      <SettingsProfileAppearance />

      <div className="grid gap-4 xl:grid-cols-2 xl:items-start">
        <SettingsCategoriesSection compact initialCategories={[]} />

        <div id="settings-rules" className="scroll-mt-6">
          <RulesContent compact embedded initialCategories={[]} initialRules={[]} />
        </div>
      </div>
    </section>
  );
}
