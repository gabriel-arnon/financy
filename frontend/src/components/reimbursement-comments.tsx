"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { MessageSquare, RefreshCw, Send, Trash2, X } from "lucide-react";
import { ApiError, createReimbursementComment, deleteReimbursementComment, getReimbursementComments } from "@/lib/api";
import { cn } from "@/lib/classnames";
import type { ReimbursementComment } from "@/lib/types";
import { UiButton } from "@/components/ui-button";
import { useToast } from "@/components/toast-provider";

const COMMENT_LIMIT = 2000;

type CommentsContext = "owner" | "guest";
type AsyncState = "idle" | "loading" | "sending" | "deleting";

interface ReimbursementCommentsProps {
  claimId: string;
  context: CommentsContext;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function errorMessage(err: unknown) {
  if (err instanceof ApiError) {
    if (err.status === 401) return "Sua sessao expirou. Entre novamente.";
    if (err.status === 403) return "Voce nao tem permissao para acessar os comentarios deste ressarcimento.";
    if (err.status === 404) return "Este ressarcimento nao foi encontrado ou nao esta mais disponivel.";
    if (err.status === 409) return "Esta acao nao pode ser concluida no estado atual do ressarcimento.";
    if (err.status === 422) return "Revise o comentario informado.";
    if (err.status === 429) return "Muitas tentativas. Aguarde alguns instantes e tente novamente.";
    if (err.status >= 500) return "Falha ao processar comentarios. Tente novamente em alguns instantes.";
  }
  return err instanceof Error ? err.message : "Falha ao processar comentarios.";
}

function authorLabel(comment: ReimbursementComment) {
  if (comment.is_mine) return "Voce";
  if (comment.author_role === "owner") return "Responsavel";
  return "Convidado";
}

function canDelete(comment: ReimbursementComment, context: CommentsContext) {
  return comment.is_mine || context === "owner";
}

export function ReimbursementComments({ claimId, context }: ReimbursementCommentsProps) {
  const toast = useToast();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const cancelDeleteRef = useRef<HTMLButtonElement | null>(null);
  const [comments, setComments] = useState<ReimbursementComment[]>([]);
  const [body, setBody] = useState("");
  const [loadedClaimId, setLoadedClaimId] = useState<string | null>(null);
  const [state, setState] = useState<AsyncState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ReimbursementComment | null>(null);
  const trimmedBody = body.trim();
  const isTooLong = body.length > COMMENT_LIMIT;
  const isLoading = state === "loading" || loadedClaimId !== claimId;
  const canSubmit = trimmedBody.length > 0 && !isTooLong && state !== "sending" && !isLoading;

  const countLabel = useMemo(() => `${comments.length} comentario${comments.length === 1 ? "" : "s"}`, [comments.length]);

  useEffect(() => {
    let active = true;
    getReimbursementComments(claimId, { limit: 100 })
      .then((items) => {
        if (!active) return;
        setComments(items);
        setLoadedClaimId(claimId);
        setError(null);
        setState("idle");
      })
      .catch((err) => {
        if (!active) return;
        setError(errorMessage(err));
        setComments([]);
        setLoadedClaimId(claimId);
        setState("idle");
      });
    return () => {
      active = false;
    };
  }, [claimId]);

  useEffect(() => {
    if (!deleteTarget) return;
    window.setTimeout(() => cancelDeleteRef.current?.focus(), 0);
  }, [deleteTarget]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && deleteTarget && state !== "deleting") {
        setDeleteTarget(null);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [deleteTarget, state]);

  async function reload() {
    setState("loading");
    setLoadedClaimId(null);
    setError(null);
    try {
      setComments(await getReimbursementComments(claimId, { limit: 100 }));
      setLoadedClaimId(claimId);
    } catch (err) {
      setError(errorMessage(err));
      setComments([]);
      setLoadedClaimId(claimId);
    } finally {
      setState("idle");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setState("sending");
    setError(null);
    try {
      const created = await createReimbursementComment(claimId, trimmedBody);
      setComments((current) => [...current, created]);
      setBody("");
      toast.success("Comentario enviado.");
      window.setTimeout(() => textareaRef.current?.focus(), 0);
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      toast.error(message);
    } finally {
      setState("idle");
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setState("deleting");
    setError(null);
    try {
      await deleteReimbursementComment(claimId, deleteTarget.id);
      setComments((current) => current.filter((comment) => comment.id !== deleteTarget.id));
      setDeleteTarget(null);
      toast.danger("Comentario excluido.");
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      toast.error(message);
    } finally {
      setState("idle");
    }
  }

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-mint" />
            <h3 className="text-sm font-semibold text-ink">Comentarios</h3>
          </div>
          <p className="mt-1 text-xs text-stone-500">{countLabel}</p>
        </div>
        <UiButton icon={<RefreshCw className="h-4 w-4" />} onClick={() => { void reload(); }} size="sm" variant="ghost" disabled={state === "loading"}>
          Tentar novamente
        </UiButton>
      </div>

      <div className="mt-4 grid gap-3">
        {isLoading ? (
          <div className="grid gap-2" aria-label="Carregando comentarios">
            <div className="h-16 animate-pulse rounded-md bg-stone-100" />
            <div className="h-16 animate-pulse rounded-md bg-stone-100" />
          </div>
        ) : null}

        {error && !isLoading ? (
          <div className="rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-900">
            <p>{error}</p>
            <button className="mt-2 text-sm font-semibold underline" onClick={() => { void reload(); }} type="button">
              Tentar novamente
            </button>
          </div>
        ) : null}

        {!isLoading && !error && comments.length === 0 ? (
          <p className="rounded-md bg-stone-50 p-3 text-sm text-stone-500">Ainda nao ha comentarios neste ressarcimento.</p>
        ) : null}

        {!isLoading && comments.length > 0 ? (
          <div className="grid gap-2" aria-label="Lista de comentarios">
            {comments.map((comment) => (
              <article key={comment.id} className={cn("rounded-md border px-3 py-2", comment.is_mine ? "border-emerald-100 bg-emerald-50/60" : "border-stone-200 bg-stone-50")}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-ink">{authorLabel(comment)}</p>
                    <p className="mt-0.5 text-xs text-stone-500">{formatDateTime(comment.created_at)}</p>
                  </div>
                  {canDelete(comment, context) ? (
                    <button
                      aria-label={`Excluir comentario de ${authorLabel(comment)}`}
                      className="rounded-md p-2 text-stone-500 hover:bg-white hover:text-red-700"
                      disabled={state === "deleting"}
                      onClick={() => setDeleteTarget(comment)}
                      type="button"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-stone-700">{comment.body}</p>
              </article>
            ))}
          </div>
        ) : null}
      </div>

      <form className="mt-4 grid gap-2" onSubmit={submit}>
        <label className="grid gap-1.5 text-sm font-medium text-ink" htmlFor={`comment-${claimId}`}>
          Novo comentario
          <textarea
            ref={textareaRef}
            id={`comment-${claimId}`}
            className="min-h-24 rounded-md border border-stone-200 px-3 py-2 text-sm font-normal outline-none focus:border-mint disabled:bg-stone-50"
            maxLength={COMMENT_LIMIT + 200}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Escreva uma observacao para este ressarcimento"
            value={body}
            disabled={state === "sending"}
          />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className={cn("text-xs", isTooLong ? "text-red-700" : "text-stone-500")}>{body.length}/{COMMENT_LIMIT}</p>
          <UiButton icon={<Send className="h-4 w-4" />} type="submit" variant="primary" disabled={!canSubmit}>
            {state === "sending" ? "Enviando..." : "Enviar comentario"}
          </UiButton>
        </div>
      </form>

      {deleteTarget ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-4 sm:items-center">
          <div aria-labelledby="delete-comment-title" aria-modal="true" className="w-full max-w-md rounded-lg border border-stone-200 bg-white p-5 shadow-2xl" role="dialog">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="delete-comment-title" className="text-lg font-semibold text-ink">Excluir comentario</h2>
                <p className="mt-2 text-sm leading-6 text-stone-600">O comentario deixara de aparecer na conversa, mas o historico sera preservado.</p>
              </div>
              <button aria-label="Fechar" className="rounded-md p-2 text-stone-500 hover:bg-stone-100" onClick={() => setDeleteTarget(null)} type="button" disabled={state === "deleting"}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <UiButton ref={cancelDeleteRef} onClick={() => setDeleteTarget(null)} variant="ghost" disabled={state === "deleting"}>
                Voltar
              </UiButton>
              <UiButton icon={<Trash2 className="h-4 w-4" />} onClick={() => { void confirmDelete(); }} variant="danger" disabled={state === "deleting"}>
                {state === "deleting" ? "Excluindo..." : "Excluir comentario"}
              </UiButton>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
