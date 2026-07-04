"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { deleteStatement } from "@/lib/api";

interface StatementDeleteButtonProps {
  statementId: string;
  compact?: boolean;
  redirectTo?: string;
}

export function StatementDeleteButton({ statementId, compact = false, redirectTo }: StatementDeleteButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (!window.confirm("Excluir esta fatura sem transações?")) return;
    setLoading(true);
    setError(null);
    try {
      await deleteStatement(statementId);
      if (redirectTo) {
        router.push(redirectTo);
      } else {
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir fatura.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-1">
      <UiButton
        disabled={loading}
        icon={<Trash2 className="h-4 w-4" />}
        onClick={handleClick}
        size={compact ? "sm" : "md"}
        variant="danger"
      >
        {loading ? "Excluindo..." : "Excluir fatura"}
      </UiButton>
      {error ? <p className="text-xs text-red-700">{error}</p> : null}
    </div>
  );
}
