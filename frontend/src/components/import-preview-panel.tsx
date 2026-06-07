"use client";

import { useEffect, useState } from "react";
import { getImportPreview } from "@/lib/api";
import type { ImportPreviewResponse } from "@/lib/types";
import { ImportPreviewTable } from "@/components/import-preview-table";

export function ImportPreviewPanel({ importId }: { importId: string }) {
  const [data, setData] = useState<ImportPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getImportPreview(importId)
      .then((response) => {
        if (active) setData(response);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Falha ao carregar prévia");
      });
    return () => {
      active = false;
    };
  }, [importId]);

  if (error) return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!data) return <p className="text-sm text-stone-500">Carregando prévia...</p>;

  return <ImportPreviewTable importId={importId} items={data.items} categories={data.categories} />;
}
