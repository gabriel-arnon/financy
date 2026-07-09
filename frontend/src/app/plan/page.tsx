import { Crown } from "lucide-react";

export default function PlanPage() {
  return (
    <section className="space-y-6">
      <div className="flex items-start gap-3">
        <Crown className="mt-1 h-7 w-7 text-mint" />
        <div>
          <p className="text-sm font-medium text-mint">Plano</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Plano</h1>
          <p className="mt-2 text-sm text-stone-600">Gerenciamento de plano em breve.</p>
        </div>
      </div>
    </section>
  );
}
