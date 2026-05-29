import { HealthResponse } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

interface Props {
  health: HealthResponse;
}

export function CircuitBreakerBanner({ health }: Props) {
  const active = health.circuit_breakers_active;

  if (!active || active.length === 0) return null;

  const labels: Record<string, string> = {
    DRAWDOWN:      "Portfolio drawdown ≥ 10% — no new BUY orders",
    CONCENTRATION: "Position concentration ≥ 15% NAV — no adds",
    SECTOR_CAP:    "Sector allocation ≥ 40% NAV — no adds in that sector",
    LLM_COST:      "Daily LLM budget exceeded — downgraded to cheaper models",
    RESTRICTED:    "One or more stocks on NSE ASM/GSM list — forced exit pending",
  };

  return (
    <div className="rounded-lg border border-bear/40 bg-bear/10 p-4 mb-6">
      <div className="flex items-start gap-3">
        <AlertTriangle className="text-bear mt-0.5 shrink-0" size={18} />
        <div>
          <p className="text-bear font-semibold text-sm mb-1">
            Circuit Breaker{active.length > 1 ? "s" : ""} Active
          </p>
          <ul className="space-y-0.5">
            {active.map((cb) => (
              <li key={cb} className="text-xs text-subtle">
                <span className="text-bear font-mono mr-1">{cb}:</span>
                {labels[cb] ?? cb}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
