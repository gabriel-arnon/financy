import { SlidersHorizontal } from "lucide-react";
import { RulesContent } from "@/components/rules-content";
import { SettingsCategoriesSection } from "@/components/settings-categories-section";
import { SettingsProfileAppearance } from "@/components/settings-profile-appearance";

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
