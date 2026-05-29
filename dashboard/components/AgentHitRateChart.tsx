"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { AgentHitRate } from "@/lib/api";

interface Props {
  agentHitRates: AgentHitRate[];
}

const AGENT_SHORT: Record<string, string> = {
  NewsSentiment:    "News",
  Technical:        "Tech",
  Fundamentals:     "Fund",
  BullBear:         "Bull/Bear",
  PortfolioManager: "PM",
};

export function AgentHitRateChart({ agentHitRates }: Props) {
  if (agentHitRates.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-subtle text-sm">
        No hit-rate data yet.
      </div>
    );
  }

  const data = agentHitRates.map((a) => ({
    agent: AGENT_SHORT[a.agent] ?? a.agent,
    hit_rate: Math.round(a.hit_rate * 100),
    n_calls: a.n_calls,
    confidence: Math.round(a.avg_confidence * 100),
  }));

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3142" vertical={false} />
          <XAxis
            dataKey="agent"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={{ stroke: "#2d3142" }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1a1d27",
              border: "1px solid #2d3142",
              borderRadius: 8,
              color: "#e2e8f0",
              fontSize: 11,
            }}
            formatter={(value: number, name: string) =>
              name === "hit_rate" ? [`${value}%`, "Hit Rate"] : [value, name]
            }
          />
          <Bar dataKey="hit_rate" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={
                  entry.hit_rate >= 60
                    ? "#22c55e"
                    : entry.hit_rate >= 45
                    ? "#f59e0b"
                    : "#ef4444"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Detail table */}
      <div className="text-xs space-y-1">
        {agentHitRates.map((a) => (
          <div
            key={a.agent}
            className="flex justify-between text-subtle py-1 border-b border-border/50"
          >
            <span>{a.agent}</span>
            <span className="font-mono space-x-3">
              <span>{Math.round(a.hit_rate * 100)}% hit</span>
              <span className="text-muted">{a.n_calls} calls</span>
              <span className="text-muted">
                {Math.round(a.avg_confidence * 100)}% avg conf
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
