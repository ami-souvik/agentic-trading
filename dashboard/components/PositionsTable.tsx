import { PositionResponse, formatINR, formatPct, pnlColor } from "@/lib/api";
import clsx from "clsx";

interface Props {
  positions: PositionResponse[];
  openCount: number;
  maxPositions: number;
}

export function PositionsTable({ positions, openCount, maxPositions }: Props) {
  if (positions.length === 0) {
    return (
      <div className="text-center py-8 text-subtle text-sm">
        No open positions — portfolio is in cash.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-subtle border-b border-border">
            <th className="pb-2 pr-4 font-medium">Ticker</th>
            <th className="pb-2 pr-4 font-medium text-right">Qty</th>
            <th className="pb-2 pr-4 font-medium text-right">Avg Price</th>
            <th className="pb-2 pr-4 font-medium text-right">Stop Loss</th>
            <th className="pb-2 pr-4 font-medium text-right">Target</th>
            <th className="pb-2 pr-4 font-medium text-right">Days Held</th>
            <th className="pb-2 pr-4 font-medium text-right">P&amp;L</th>
            <th className="pb-2 font-medium">Sector</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const daysBar = Math.min(pos.days_held / pos.horizon_days, 1);
            const daysColor =
              daysBar > 0.8
                ? "bg-bear"
                : daysBar > 0.5
                ? "bg-gold"
                : "bg-bull";

            return (
              <tr
                key={pos.ticker}
                className="border-b border-border/50 hover:bg-surface/50 transition-colors"
              >
                {/* Ticker */}
                <td className="py-3 pr-4">
                  <div className="font-mono font-semibold text-text">
                    {pos.ticker}
                  </div>
                  <div className="text-xs text-subtle">
                    Entry {pos.entry_date}
                  </div>
                </td>

                {/* Qty */}
                <td className="py-3 pr-4 text-right font-mono">{pos.qty}</td>

                {/* Avg Price */}
                <td className="py-3 pr-4 text-right font-mono">
                  ₹{pos.avg_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </td>

                {/* Stop Loss */}
                <td className="py-3 pr-4 text-right font-mono text-bear">
                  ₹{pos.stop_loss_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </td>

                {/* Target */}
                <td className="py-3 pr-4 text-right font-mono text-bull">
                  ₹{pos.target_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </td>

                {/* Days Held / horizon mini bar */}
                <td className="py-3 pr-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <span className="font-mono">
                      {pos.days_held}/{pos.horizon_days}d
                    </span>
                    <div className="w-12 h-1.5 bg-border rounded-full overflow-hidden">
                      <div
                        className={clsx("h-full rounded-full transition-all", daysColor)}
                        style={{ width: `${daysBar * 100}%` }}
                      />
                    </div>
                  </div>
                </td>

                {/* Unrealised P&L */}
                <td className="py-3 pr-4 text-right">
                  {pos.unrealized_pnl_pct !== null ? (
                    <span className={clsx("font-mono", pnlColor(pos.unrealized_pnl_pct))}>
                      {formatPct(pos.unrealized_pnl_pct)}
                    </span>
                  ) : (
                    <span className="text-subtle text-xs">—</span>
                  )}
                </td>

                {/* Sector */}
                <td className="py-3 text-subtle text-xs">{pos.sector}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Slot usage */}
      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-subtle">
          Positions: {openCount} / {maxPositions}
        </span>
        <div className="flex gap-1">
          {Array.from({ length: maxPositions }, (_, i) => (
            <div
              key={i}
              className={clsx(
                "w-2 h-2 rounded-full",
                i < openCount ? "bg-accent" : "bg-border"
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
