/**
 * Analytics / Metrics page.
 *
 * Shows benchmark comparison, per-agent hit rates, LLM cost breakdown,
 * and a statistical significance warning.
 */
import { api, formatPct } from "@/lib/api";
import { BenchmarkChart } from "@/components/BenchmarkChart";
import { AgentHitRateChart } from "@/components/AgentHitRateChart";
import { RefreshButton } from "@/components/RefreshButton";

export const revalidate = 120;  // analytics is slow — cache for 2 min

export default async function MetricsPage() {
  let data = null;
  let navData = null;
  let error: string | null = null;

  try {
    [data, navData] = await Promise.all([
      api.analytics(),
      api.dailyNav(),
    ]);
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load analytics";
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text">Performance Analytics</h1>
          <p className="text-xs text-subtle mt-0.5">
            Strategy vs benchmarks · Per-agent signal quality · LLM cost breakdown
          </p>
        </div>
        <RefreshButton />
      </div>

      {error && (
        <div className="rounded-lg border border-bear/40 bg-bear/10 p-4 text-bear text-sm">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Statistical warning */}
          <div className="rounded-lg border border-gold/30 bg-gold/5 p-4 text-gold text-xs">
            ⚠ {data.statistical_warning}
          </div>

          {/* Key metrics strip */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: "Sharpe", value: data.sharpe.toFixed(2) },
              { label: "Sortino", value: data.sortino.toFixed(2) },
              { label: "Max Drawdown", value: formatPct(data.max_drawdown_pct) },
              { label: "Win Rate", value: formatPct(data.win_rate * 100, 1) },
              { label: "Profit Factor", value: data.profit_factor.toFixed(2) },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl border border-border bg-surface p-4">
                <p className="text-xs text-subtle">{label}</p>
                <p className="text-xl font-semibold font-mono mt-1 text-text">{value}</p>
              </div>
            ))}
          </div>

          {/* Benchmark chart */}
          <div className="rounded-xl border border-border bg-surface p-4">
            <h2 className="text-sm font-semibold text-subtle mb-4">
              Portfolio vs Benchmarks
            </h2>
            <BenchmarkChart
              portfolioNav={navData?.points ?? []}
              benchmarks={data.benchmark_comparison}
              initialCapital={1_000_000}
            />
          </div>

          {/* Two-column: agent hit rates + cost breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Agent hit rates */}
            <div className="rounded-xl border border-border bg-surface p-4">
              <h2 className="text-sm font-semibold text-subtle mb-4">
                Per-Agent Signal Quality
              </h2>
              <p className="text-xs text-subtle mb-3">
                Hit rate = % of directional calls that aligned with market direction (Nifty proxy).
                Does not account for magnitude — use as a relative ranking only.
              </p>
              <AgentHitRateChart agentHitRates={data.agent_hit_rates} />
            </div>

            {/* LLM cost breakdown */}
            <div className="rounded-xl border border-border bg-surface p-4">
              <h2 className="text-sm font-semibold text-subtle mb-4">
                LLM Cost Breakdown
              </h2>
              {data.agent_cost_breakdown.length === 0 ? (
                <p className="text-subtle text-sm text-center py-8">
                  No cost data yet — run the pipeline first.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-subtle border-b border-border">
                        <th className="text-left pb-2">Agent</th>
                        <th className="text-left pb-2">Model</th>
                        <th className="text-right pb-2">Calls</th>
                        <th className="text-right pb-2">Cost</th>
                        <th className="text-right pb-2">Tokens↑</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.agent_cost_breakdown.map((row) => (
                        <tr
                          key={`${row.agent}-${row.model}`}
                          className="border-b border-border/50"
                        >
                          <td className="py-2 text-text">{row.agent}</td>
                          <td className="py-2 font-mono text-subtle">{row.model}</td>
                          <td className="py-2 text-right text-subtle">{row.call_count}</td>
                          <td className="py-2 text-right font-mono text-gold">
                            ${row.total_cost_usd.toFixed(4)}
                          </td>
                          <td className="py-2 text-right font-mono text-subtle">
                            {row.total_input_tokens.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-border">
                        <td colSpan={3} className="pt-2 text-subtle">Total</td>
                        <td className="pt-2 text-right font-mono text-gold font-semibold">
                          ${data.agent_cost_breakdown
                            .reduce((s, r) => s + r.total_cost_usd, 0)
                            .toFixed(4)}
                        </td>
                        <td className="pt-2 text-right font-mono text-subtle">
                          {data.agent_cost_breakdown
                            .reduce((s, r) => s + r.total_input_tokens, 0)
                            .toLocaleString()}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
