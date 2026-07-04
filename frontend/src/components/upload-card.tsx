"use client";

import type { ChangeEvent, DragEvent } from "react";
import { useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { uploadImport } from "@/lib/api";

const MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024;

interface UploadCardProps {
  onUploaded: (importId: string) => void;
}

export function UploadCard({ onUploaded }: UploadCardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  async function uploadFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      setSuccess(null);
      setError("Arquivo muito grande para o deploy atual. Envie um arquivo de ate 8 MB.");
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await uploadImport(file);
      setSuccess("Upload concluído. Abrindo prévia...");
      onUploaded(response.import_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao importar arquivo. Tente um arquivo menor ou verifique a conexao.");
    } finally {
      setLoading(false);
    }
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    void uploadFile(file);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
    void uploadFile(event.dataTransfer.files?.[0]);
  }

  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <label
        htmlFor="import-file-input"
        className={`flex min-h-52 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 text-center transition ${
          dragActive ? "border-mint bg-emerald-50" : "border-stone-300 bg-stone-50 hover:border-mint"
        }`}
        aria-disabled={loading}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        {loading ? <Loader2 className="h-10 w-10 animate-spin text-mint" /> : <FileUp className="h-10 w-10 text-mint" />}
        <span className="text-lg font-semibold text-ink">{loading ? "Enviando..." : "Arraste um arquivo ou clique para enviar"}</span>
        <span className="max-w-md text-sm leading-6 text-stone-500">
          PDF, OFX, CSV e XLSX são processados em prévia antes de qualquer lançamento ser salvo.
        </span>
      </label>
      <input
        id="import-file-input"
        className="sr-only"
        type="file"
        accept=".pdf,.ofx,.csv,.xlsx"
        onChange={handleChange}
        disabled={loading}
      />
      {error ? <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
      {success ? <p className="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{success}</p> : null}
    </div>
  );
}
