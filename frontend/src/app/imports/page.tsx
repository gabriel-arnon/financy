"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { UploadCard } from "@/components/upload-card";
import { ImportPreviewPanel } from "@/components/import-preview-panel";

function ImportsPageContent() {
  const searchParams = useSearchParams();
  const [uploadedImportId, setUploadedImportId] = useState<string | null>(null);
  const importId = uploadedImportId ?? searchParams.get("importId");

  function handleUploaded(nextImportId: string) {
    setUploadedImportId(nextImportId);
    window.history.replaceState(null, "", `/importacao?importId=${nextImportId}`);
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">Importação</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Enviar fatura ou extrato</h1>
      </div>
      <UploadCard onUploaded={handleUploaded} />
      {importId ? <ImportPreviewPanel importId={importId} /> : null}
    </section>
  );
}

export default function ImportsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-stone-500">Carregando importação...</p>}>
      <ImportsPageContent />
    </Suspense>
  );
}
