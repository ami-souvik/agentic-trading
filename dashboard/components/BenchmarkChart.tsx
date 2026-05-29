"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { DailyNavPoint, BenchmarkComparison, formatINR } from "@/lib/api";

interface Props {
  portfolioNav: DailyNavPoint[];
  benchmarks: BenchmarkComparison;
  initialCapital: number;
}

function shortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

const LINES = [
  { key: "portfolio",        label: "Portfolio",      color: "#6366f1", dash: "none" },
  { key: "nifty50_tri",      label: "Nifty 50 TRI",   color: "#f59e0b", dash: "5 3" },
  { key: "equal_weight",     label: "Equal Weight",   color: "#94a3b8", dash: "4 4" },
  { key: "momentum_5d",      label: "Momentum 5d",    color: "#22c55e", dash: "3 3" },
  { key: "mean_reversion_5d",label: "Mean Reversion", color: "#ef4444", dash: "3 3" },
];

export function BenchmarkChart({ portfolioNav, benchmarks, initialCapital }: Props) {
  // Build date-keyed map
  const portMap = new Map(portfolioNav.map((p) => [p.date, p.nav]));
  const niftyMap = new Map(benchmarks.nifty50_tri.map((p) => [p.date, p.nav]));
  const ewMap    = new Map(benchmarks.equal_weight.map((p) => [p.date, p.nav]));
  const momMap   = new Map(benchmarks.momentum_5d.map((p) => [p.date, p.nav]));
  const mrMap    = new Map(benchmarks.mean_reversion_5d.map((p) => [p.date, p.nav]));

  // Union of all dates
  const allDates = Array.from(
    new Set([
      ...portfolioNav.map((p) => p.date),
      ...benchmarks.nifty50_tri.map((p) => p.date),
    ])
  ).sort();

  const data = allDates.map((d) => ({
    date: shortDate(d),
    portfolio:         portMap.get(d) ?? initialCapital,
    nifty50_tri:       niftyMap.get(d) ?? initialCapital,
    equal_weight:      ewMap.get(d) ?? initialCapital,
    momentum_5d:       momMap.get(d) ?? initialCapital,
    mean_reversion_5d: mrMap.get(d) ?? initialCapital,
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-subtle text-sm">
        No data yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d3142" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          axisLine={{ stroke: "#2d3142" }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v) => formatINR(v)}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          axisLine={{ stroke: "#2d3142" }}
          tickLine={false}
          width={80}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1d27",
            border: "1px solid #2d3142",
            borderRadius: 8,
            color: "#e2e8f0",
            fontSize: 11,
          }}
          formatter={(value: number, name: string) => {
            const label = LINES.find((l) => l.key === name)?.label ?? name;
            return [formatINR(value, 0), label];
          }}
        />
        <Legend
          formatter={(value) => LINES.find((l) => l.key === value)?.label ?? value}
          wrapperStyle={{ color: "#94a3b8", fontSize: 11 }}
        />
        {LINES.map(({ key, color, dash }) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={color}
            strokeWidth={key === "portfolio" ? 2 : 1.5}
            strokeDasharray={dash === "none" ? undefined : dash}
            dot={false}
            activeDot={{ r: 3, fill: color }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
