"use client";

import { useState } from "react";
import { UploadCard } from "@/components/upload-card";
import { ImportPreviewPanel } from "@/components/import-preview-panel";

export default function ImportsPage() {
  const [importId, setImportId] = useState<string | null>(null);

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-mint">Importação</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Enviar fatura ou extrato</h1>
      </div>
      <UploadCard onUploaded={setImportId} />
      {importId ? <ImportPreviewPanel importId={importId} /> : null}
    </section>
  );
}
