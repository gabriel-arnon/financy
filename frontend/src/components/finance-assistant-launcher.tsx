"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { UiButton } from "@/components/ui-button";
import { askAiFinance } from "@/lib/api";
import type { AiFinanceQuestionResponse } from "@/lib/types";

interface AssistantMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  response?: AiFinanceQuestionResponse;
}

function ctaHref(response: AiFinanceQuestionResponse) {
  if (!response.cta) return null;
  const search = new URLSearchParams(response.cta.query);
  return `${response.cta.route}${search.toString() ? `?${search.toString()}` : ""}`;
}

export function FinanceAssistantLauncher() {
  const router = useRouter();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (!open) return;
    window.setTimeout(() => inputRef.current?.focus(), 0);

    function handlePointerDown(event: PointerEvent) {
      if (!panelRef.current?.contains(event.target as Node)) setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3 || isSending) return;
    const userMessage: AssistantMessage = { id: Date.now(), role: "user", text: trimmed };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setIsSending(true);
    try {
      const response = await askAiFinance(trimmed);
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: response.message || response.answer,
          response,
        },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, role: "assistant", text: "Nao consegui responder agora. Tente novamente em alguns segundos." },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function navigateToCta(response: AiFinanceQuestionResponse) {
    const href = ctaHref(response);
    if (!href) return;
    setOpen(false);
    router.push(href);
  }

  return (
    <div className="fixed bottom-5 right-5 z-[70]">
      {open ? (
        <div ref={panelRef} aria-label="Assistente financeiro" className="mb-3 flex h-[min(34rem,calc(100vh-6rem))] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-lg border border-stone-200 bg-white shadow-2xl" role="dialog" aria-modal="false">
          <div className="flex items-center justify-between gap-3 border-b border-stone-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-ink text-white">
                <Bot className="h-4 w-4" />
              </span>
              <p className="text-sm font-semibold text-ink">Assistente financeiro</p>
            </div>
            <button className="rounded-md border border-stone-200 p-2 text-stone-600 transition hover:bg-stone-50" type="button" aria-label="Fechar assistente" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 ? (
              <p className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-600">Pergunte sobre gastos, categorias ou um periodo especifico.</p>
            ) : null}
            {messages.map((message) => (
              <div key={message.id} className={message.role === "user" ? "ml-8 rounded-md bg-ink px-3 py-2 text-sm text-white" : "mr-8 rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-700"}>
                <p>{message.text}</p>
                {message.response?.cta ? (
                  <UiButton className="mt-3" onClick={() => navigateToCta(message.response!)} size="sm" variant="secondary">
                    {message.response.cta.label}
                  </UiButton>
                ) : null}
              </div>
            ))}
            {isSending ? (
              <p className="inline-flex items-center gap-2 rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Analisando...
              </p>
            ) : null}
          </div>
          <form className="flex gap-2 border-t border-stone-100 p-3" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              aria-label="Pergunte sobre suas financas"
              className="h-10 min-w-0 flex-1 rounded-md border border-stone-200 px-3 text-sm outline-none focus:border-mint"
              disabled={isSending}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ex: quanto gastei com assinaturas esse mes"
              value={question}
            />
            <UiButton aria-label="Enviar pergunta" disabled={isSending || question.trim().length < 3} icon={isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} type="submit" variant="primary" />
          </form>
        </div>
      ) : null}
      <button
        aria-label={open ? "Assistente financeiro aberto" : "Abrir assistente financeiro"}
        aria-expanded={open}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-ink text-white shadow-xl ring-1 ring-black/10 transition hover:-translate-y-0.5 hover:bg-stone-900 focus:outline-none focus:ring-2 focus:ring-mint/60"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <Bot className="h-6 w-6" />
      </button>
    </div>
  );
}
