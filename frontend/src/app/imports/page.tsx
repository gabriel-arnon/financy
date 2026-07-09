"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Plus } from "lucide-react";
import { UploadCard } from "@/components/upload-card";
import { ImportPreviewPanel } from "@/components/import-preview-panel";
import { UiButton } from "@/components/ui-button";

function ImportsFallback() {
  return (
    <section className="space-y-6" aria-busy="true" aria-live="polite">
      <div>
        <div className="h-4 w-24 animate-pulse rounded-md bg-stone-100" />
        <div className="mt-3 h-8 w-72 max-w-full animate-pulse rounded-md bg-stone-100" />
      </div>
      <div className="rounded-lg border border-stone-200 bg-white p-8 shadow-sm">
        <div className="mx-auto h-12 w-12 animate-pulse rounded-full bg-stone-100" />
        <div className="mx-auto mt-5 h-5 w-72 max-w-full animate-pulse rounded-md bg-stone-100" />
        <div className="mx-auto mt-3 h-4 w-48 max-w-full animate-pulse rounded-md bg-stone-100" />
      </div>
    </section>
  );
}

function ImportsPageContent() {
  const searchParams = useSearchParams();
  const [uploadedImportId, setUploadedImportId] = useState<string | null>(null);
  const importId = uploadedImportId ?? searchParams.get("importId");

  function handleUploaded(nextImportId: string) {
    setUploadedImportId(nextImportId);
    window.history.replaceState(null, "", `/importacao?importId=${nextImportId}`);
  }

  function handleNewImport() {
    setUploadedImportId(null);
    window.history.replaceState(null, "", "/importacao");
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-mint">Importacao</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Enviar fatura ou extrato</h1>
        </div>
        {importId ? (
          <UiButton icon={<Plus className="h-4 w-4" />} onClick={handleNewImport} variant="secondary">
            Nova importação
          </UiButton>
        ) : null}
      </div>
      {!importId ? <UploadCard onUploaded={handleUploaded} /> : null}
      {importId ? <ImportPreviewPanel importId={importId} /> : null}
    </section>
  );
}

export default function ImportsPage() {
  return (
    <Suspense fallback={<ImportsFallback />}>
      <ImportsPageContent />
    </Suspense>
  );
}
