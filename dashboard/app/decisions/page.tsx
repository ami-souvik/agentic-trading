/**
 * Decisions page — decision log viewer.
 *
 * Shows all 15 ticker decisions for a selected date. Each ticker is a
 * collapsible DecisionCard with all 5 agent outputs.
 */
import { api } from "@/lib/api";
import { DecisionCard } from "@/components/DecisionCard";
import { DecisionsDatePicker } from "@/components/DecisionsDatePicker";
import { RefreshButton } from "@/components/RefreshButton";

export const revalidate = 60;

interface Props {
  searchParams: { date?: string };
}

export default async function DecisionsPage({ searchParams }: Props) {
  const selectedDate =
    searchParams.date ?? new Date().toISOString().split("T")[0];

  let data = null;
  let error: string | null = null;

  try {
    data = await api.decisions(selectedDate);
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load decisions";
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text">Decision Log</h1>
          <p className="text-xs text-subtle mt-0.5">
            5-agent pipeline outputs for all 15 tickers
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DecisionsDatePicker selectedDate={selectedDate} />
          <RefreshButton />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-bear/40 bg-bear/10 p-4 text-bear text-sm">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!error && data && data.decisions.length === 0 && (
        <div className="text-center py-24 text-subtle text-sm">
          No decisions recorded for {selectedDate}.
          <br />
          <span className="text-xs">
            Run the daily pipeline or select a different date.
          </span>
        </div>
      )}

      {/* Decision summary strip */}
      {data && data.decisions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {(["BUY", "HOLD", "EXIT", "SKIP"] as const).map((action) => {
            const count = data.decisions.filter(
              (d) => d.pm_decision === action
            ).length;
            if (count === 0) return null;
            const colors: Record<string, string> = {
              BUY:  "bg-bull/10 text-bull border-bull/20",
              HOLD: "bg-gold/10 text-gold border-gold/20",
              EXIT: "bg-bear/10 text-bear border-bear/20",
              SKIP: "bg-muted/10 text-subtle border-muted/20",
            };
            return (
              <span
                key={action}
                className={`px-3 py-1 rounded-full text-xs border ${colors[action]}`}
              >
                {count} {action}
              </span>
            );
          })}
          <span className="px-3 py-1 rounded-full text-xs border border-border text-subtle">
            {data.total} total
          </span>
        </div>
      )}

      {/* Decision cards */}
      {data && (
        <div className="space-y-3">
          {data.decisions.map((decision) => (
            <DecisionCard key={decision.ticker} decision={decision} />
          ))}
        </div>
      )}
    </div>
  );
}
