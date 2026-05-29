interface Props {
  costUsd: number;
  budgetUsd?: number;
}

export function AgentCostWidget({ costUsd, budgetUsd = 1.0 }: Props) {
  const pct = Math.min((costUsd / budgetUsd) * 100, 100);
  const color =
    pct > 90 ? "bg-bear" : pct > 60 ? "bg-gold" : "bg-bull";

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-subtle">
        <span>LLM cost today</span>
        <span>
          <span className={pct > 90 ? "text-bear font-semibold" : "text-text"}>
            ${costUsd.toFixed(4)}
          </span>
          <span className="text-subtle"> / ${budgetUsd.toFixed(2)}</span>
        </span>
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
