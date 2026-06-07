"use client";

import { ChangeEvent, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { uploadImport } from "@/lib/api";

interface UploadCardProps {
  onUploaded: (importId: string) => void;
}

export function UploadCard({ onUploaded }: UploadCardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const response = await uploadImport(file);
      onUploaded(response.import_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao importar arquivo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-dashed border-stone-300 bg-white p-6">
      <label className="flex cursor-pointer flex-col items-center justify-center gap-3 text-center">
        {loading ? <Loader2 className="h-8 w-8 animate-spin text-mint" /> : <FileUp className="h-8 w-8 text-mint" />}
        <span className="text-base font-medium text-ink">Enviar PDF, OFX, CSV ou XLSX</span>
        <span className="text-sm text-stone-500">O arquivo será processado para revisão antes de salvar.</span>
        <input className="sr-only" type="file" accept=".pdf,.ofx,.csv,.xlsx" onChange={handleChange} disabled={loading} />
      </label>
      {error ? <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
