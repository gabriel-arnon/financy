"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Check, Moon, Palette, Save, ShieldCheck, Sun, UserRound } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast-provider";
import { UiButton } from "@/components/ui-button";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";

type ThemePreference = "light" | "dark";
type DensityPreference = "comfortable" | "compact";

interface UserPreferences {
  theme: ThemePreference;
  density: DensityPreference;
  reduceMotion: boolean;
}

const preferencesKey = "financy_user_preferences";
const defaultPreferences: UserPreferences = {
  theme: "light",
  density: "comfortable",
  reduceMotion: false,
};

function readPreferences(): UserPreferences {
  if (typeof window === "undefined") return defaultPreferences;
  const stored = window.localStorage.getItem(preferencesKey);
  if (!stored) return defaultPreferences;
  try {
    const parsed = JSON.parse(stored) as Partial<UserPreferences> & { theme?: string };
    return {
      ...defaultPreferences,
      ...parsed,
      theme: parsed.theme === "dark" ? "dark" : "light",
      density: parsed.density === "compact" ? "compact" : "comfortable",
      reduceMotion: Boolean(parsed.reduceMotion),
    };
  } catch {
    return defaultPreferences;
  }
}

function readProfileName() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("financy_profile_name") ?? "";
}

function writePreferences(preferences: UserPreferences) {
  window.localStorage.setItem(preferencesKey, JSON.stringify(preferences));
  document.documentElement.dataset.theme = preferences.theme;
  document.documentElement.dataset.density = preferences.density;
  document.documentElement.dataset.reduceMotion = preferences.reduceMotion ? "true" : "false";
}

export function SettingsProfileAppearance() {
  const { session, configured } = useAuth();
  const toast = useToast();
  const supabase = getSupabaseClient();
  const metadataName = typeof session?.user.user_metadata?.full_name === "string" ? session.user.user_metadata.full_name : "";
  const fallbackName = session?.user.email?.split("@")[0] ?? readProfileName();
  const [name, setName] = useState(() => metadataName || fallbackName);
  const [preferences, setPreferences] = useState<UserPreferences>(() => readPreferences());
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPreferences, setSavingPreferences] = useState(false);

  const email = session?.user.email ?? "Usuário local";
  const initials = useMemo(() => {
    const source = (name || email).trim();
    return source.slice(0, 2).toUpperCase();
  }, [email, name]);

  useEffect(() => {
    writePreferences(preferences);
  }, [preferences]);

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextName = name.trim();
    if (!nextName) {
      toast.error("Informe um nome para salvar o perfil.");
      return;
    }

    setSavingProfile(true);
    try {
      if (configured && isSupabaseConfigured() && supabase) {
        const { error } = await supabase.auth.updateUser({ data: { full_name: nextName } });
        if (error) throw error;
      } else {
        window.localStorage.setItem("financy_profile_name", nextName);
      }
      toast.success("Perfil atualizado.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao atualizar perfil.");
    } finally {
      setSavingProfile(false);
    }
  }

  function updatePreferences(patch: Partial<UserPreferences>) {
    setPreferences((current) => ({ ...current, ...patch }));
  }

  async function handlePreferencesSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingPreferences(true);
    try {
      writePreferences(preferences);
      toast.success("Preferências salvas.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar preferências.");
    } finally {
      setSavingPreferences(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
      <article id="settings-profile" className="scroll-mt-6 rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <UserRound className="h-5 w-5 text-mint" />
          <h2 className="text-lg font-semibold text-ink">Perfil e preferências</h2>
        </div>

        <form className="mt-5 space-y-5" onSubmit={handleProfileSubmit}>
          <div className="grid gap-4 lg:grid-cols-[auto_1fr] lg:items-start">
            <div className="space-y-2">
              <p className="text-sm font-medium text-stone-600">Avatar</p>
              <div className="flex h-20 w-20 items-center justify-center rounded-full border border-mint/30 bg-emerald-50 text-lg font-semibold text-mint">
                {initials}
              </div>
            </div>

            <div className="space-y-4">
              <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Nome</span>
                  <input
                    className="h-11 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Digite seu nome"
                    value={name}
                  />
                </label>

                <UiButton disabled={savingProfile} icon={<Save className="h-4 w-4" />} type="submit" variant="primary">
                  {savingProfile ? "Salvando..." : "Salvar perfil"}
                </UiButton>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">E-mail</span>
                  <input className="h-10 w-full rounded-md border border-stone-200 bg-stone-50 px-3 text-sm text-stone-500" readOnly value={email} />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Idioma</span>
                  <input className="h-10 w-full rounded-md border border-stone-200 bg-stone-50 px-3 text-sm text-stone-500" readOnly value="Português (Brasil)" />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-stone-600">Moeda padrão</span>
                  <input className="h-10 w-full rounded-md border border-stone-200 bg-stone-50 px-3 text-sm text-stone-500" readOnly value="BRL - Real Brasileiro" />
                </label>
              </div>
            </div>
          </div>

          <div className="rounded-md border border-mint/30 bg-emerald-50 px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-mint">
              <ShieldCheck className="h-4 w-4" />
              Privacidade e Segurança
            </div>
            <p className="mt-2 text-sm leading-6 text-stone-600">
              O perfil usa a sessão autenticada e as preferências visuais ficam salvas neste navegador.
            </p>
          </div>
        </form>
      </article>

      <article id="settings-appearance" className="scroll-mt-6 rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Palette className="h-5 w-5 text-mint" />
          <h2 className="text-lg font-semibold text-ink">Aparência</h2>
        </div>

        <form className="mt-5 space-y-5" onSubmit={handlePreferencesSubmit}>
          <div className="space-y-3">
            <p className="text-sm font-medium text-stone-600">Tema</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { value: "light" as const, title: "Claro", helper: "Tema atual do Financy" },
                { value: "dark" as const, title: "Escuro", helper: "Interface com fundo escuro e menor brilho" },
              ].map((option) => {
                const selected = preferences.theme === option.value;
                return (
                  <button
                    aria-pressed={selected}
                    className={`flex items-center justify-between gap-3 rounded-md border px-4 py-3 text-left shadow-sm transition ${selected ? "border-mint bg-emerald-50" : "border-stone-200 bg-white hover:bg-stone-50"}`}
                    key={option.value}
                    onClick={() => updatePreferences({ theme: option.value })}
                    type="button"
                  >
                    <span>
                      <span className="block text-sm font-semibold text-ink">{option.title}</span>
                      <span className="mt-1 block text-xs text-stone-500">{option.helper}</span>
                    </span>
                    {selected ? (
                      <Check className="h-4 w-4 shrink-0 text-mint" />
                    ) : option.value === "dark" ? (
                      <Moon className="h-4 w-4 shrink-0 text-stone-400" />
                    ) : (
                      <Sun className="h-4 w-4 shrink-0 text-stone-400" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-stone-600">Densidade</span>
              <select
                className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm text-ink outline-none transition focus:border-mint focus:ring-2 focus:ring-mint/10"
                onChange={(event) => updatePreferences({ density: event.target.value as DensityPreference })}
                value={preferences.density}
              >
                <option value="comfortable">Confortável</option>
                <option value="compact">Compacta</option>
              </select>
            </label>

            <label className="flex items-center justify-between gap-3 rounded-md border border-stone-200 px-3 py-2">
              <span>
                <span className="block text-sm font-medium text-ink">Reduzir movimento</span>
                <span className="mt-1 block text-xs text-stone-500">Preferência salva neste navegador</span>
              </span>
              <input
                checked={preferences.reduceMotion}
                className="h-4 w-4 rounded border-stone-300"
                onChange={(event) => updatePreferences({ reduceMotion: event.target.checked })}
                type="checkbox"
              />
            </label>
          </div>

          <UiButton disabled={savingPreferences} icon={<Save className="h-4 w-4" />} type="submit" variant="primary">
            {savingPreferences ? "Salvando..." : "Salvar aparência"}
          </UiButton>
        </form>
      </article>
    </div>
  );
}
