import { Check, Palette, Save, ShieldCheck, SlidersHorizontal, UserRound } from "lucide-react";
import { RulesContent } from "@/components/rules-content";
import { SettingsCategoriesSection } from "@/components/settings-categories-section";

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
          <p className="mt-2 text-sm font-medium text-stone-600">Configure as preferências do sistema.</p>
        </div>
      </div>

      <nav
        className="sticky top-0 z-10 overflow-x-auto rounded-lg border border-stone-200 bg-white/95 p-2 shadow-sm backdrop-blur"
        aria-label="Navegação interna de configurações"
      >
        <div className="flex min-w-max gap-2">
          {settingsNav.map((item) => (
            <a
              key={item.href}
              className="inline-flex h-9 items-center justify-center whitespace-nowrap rounded-md px-3 text-sm font-medium text-stone-600 transition hover:bg-emerald-50 hover:text-mint"
              href={item.href}
            >
              {item.label}
            </a>
          ))}
        </div>
      </nav>

      <article id="settings-profile" className="scroll-mt-6 rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <UserRound className="h-5 w-5 text-mint" />
          <h2 className="text-lg font-semibold text-ink">Perfil</h2>
        </div>

        <div className="mt-5 space-y-5">
          <div className="grid gap-5 lg:grid-cols-[auto_1fr] lg:items-start">
            <div className="space-y-2">
              <p className="text-sm font-medium text-stone-600">Avatar</p>
              <div className="flex h-20 w-20 items-center justify-center rounded-full border border-stone-200 bg-stone-50 text-stone-400">
                <UserRound className="h-8 w-8" />
              </div>
            </div>

            <div className="space-y-4">
              <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Nome</span>
                  <input
                    className="h-11 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
                    defaultValue="Gabriel"
                    placeholder="Digite seu nome"
                  />
                </label>

                <button
                  className="inline-flex h-11 cursor-not-allowed items-center justify-center gap-2 whitespace-nowrap rounded-md bg-stone-200 px-4 text-sm font-medium text-stone-500 shadow-sm"
                  disabled
                  type="button"
                >
                  <Save className="h-4 w-4" />
                  Salvar
                </button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Idioma</span>
                  <input
                    className="h-10 w-full cursor-not-allowed rounded-md border border-stone-200 bg-stone-50 px-3 text-sm text-stone-500"
                    defaultValue="Português (Brasil)"
                    disabled
                    readOnly
                  />
                </label>

                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Moeda padrão</span>
                  <input
                    className="h-10 w-full cursor-not-allowed rounded-md border border-stone-200 bg-stone-50 px-3 text-sm text-stone-500"
                    defaultValue="BRL - Real Brasileiro"
                    disabled
                    readOnly
                  />
                </label>

                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Ambiente</span>
                  <input
                    className="h-10 w-full cursor-not-allowed rounded-md border border-stone-200 bg-stone-50 px-3 text-sm text-stone-500"
                    defaultValue="MVP local"
                    disabled
                    readOnly
                  />
                </label>
              </div>
            </div>
          </div>

          <p className="text-sm text-stone-500">Em breve: edição de perfil e preferências do usuário.</p>

          <div className="rounded-md border border-mint/30 bg-emerald-50 px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-mint">
              <ShieldCheck className="h-4 w-4" />
              Privacidade e Segurança
            </div>
            <p className="mt-2 text-sm leading-6 text-stone-600">
              Fazemos questão de não coletar nenhuma informação pessoal sua neste ambiente local. Seus dados financeiros são privados e seguros.
            </p>
          </div>
        </div>
      </article>

      <article id="settings-appearance" className="scroll-mt-6 rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Palette className="h-5 w-5 text-mint" />
          <h2 className="text-lg font-semibold text-ink">Aparência</h2>
        </div>
        <p className="mt-4 text-sm leading-6 text-stone-600">
          Escolha como o Financy deve apresentar a interface. A personalização completa ficará disponível em uma próxima etapa.
        </p>
        <div className="mt-5 space-y-3">
          <p className="text-sm font-medium text-stone-600">Tema</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <button
              aria-pressed="true"
              className="flex cursor-not-allowed items-center justify-between gap-3 rounded-md border border-mint bg-emerald-50 px-4 py-3 text-left shadow-sm"
              disabled
              type="button"
            >
              <span>
                <span className="block text-sm font-semibold text-ink">Claro</span>
                <span className="mt-1 block text-xs text-stone-500">Selecionado atualmente</span>
              </span>
              <Check className="h-4 w-4 shrink-0 text-mint" />
            </button>
            <button
              aria-pressed="false"
              className="flex cursor-not-allowed items-center justify-between gap-3 rounded-md border border-stone-200 bg-stone-50 px-4 py-3 text-left opacity-70"
              disabled
              type="button"
            >
              <span>
                <span className="block text-sm font-semibold text-ink">Escuro</span>
                <span className="mt-1 block text-xs text-stone-500">Indisponível no momento</span>
              </span>
            </button>
          </div>
          <p className="text-sm text-stone-500">Em breve: personalização de tema.</p>
        </div>
      </article>

      <SettingsCategoriesSection initialCategories={[]} />

      <div id="settings-rules" className="scroll-mt-6">
        <RulesContent embedded initialCategories={[]} initialRules={[]} />
      </div>
    </section>
  );
}
