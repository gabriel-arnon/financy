"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, RotateCcw } from "lucide-react";
import { UiButton } from "@/components/ui-button";
import { updateStatementStatus } from "@/lib/api";

interface StatementStatusButtonProps {
  statementId: string;
  status: string;
  compact?: boolean;
}

export function StatementStatusButton({ statementId, status, compact = false }: StatementStatusButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const isPaid = status === "paid";
  const nextStatus = isPaid ? "open" : "paid";
  const label = isPaid ? "Reabrir" : "Marcar como paga";
  const confirmMessage = isPaid ? "Reabrir esta fatura?" : "Marcar esta fatura como paga?";

  async function handleClick() {
    if (!window.confirm(confirmMessage)) return;
    setLoading(true);
    try {
      await updateStatementStatus(statementId, nextStatus);
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <UiButton
      disabled={loading}
      icon={isPaid ? <RotateCcw className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
      onClick={handleClick}
      size={compact ? "sm" : "md"}
      variant={isPaid ? "secondary" : "primary"}
    >
      {loading ? "Salvando..." : label}
    </UiButton>
  );
}
