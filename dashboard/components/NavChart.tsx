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
import { DailyNavPoint, BenchmarkPoint, formatINR } from "@/lib/api";

interface Props {
  navPoints: DailyNavPoint[];
  niftyPoints: BenchmarkPoint[];
  initialCapital: number;
}

interface ChartPoint {
  date: string;
  portfolio: number;
  nifty: number;
}

function shortDate(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export function NavChart({ navPoints, niftyPoints, initialCapital }: Props) {
  // Merge nav + nifty into one series by date
  const niftyMap = new Map(niftyPoints.map((p) => [p.date, p.nav]));

  const data: ChartPoint[] = navPoints.map((p) => ({
    date: shortDate(p.date),
    portfolio: p.nav,
    nifty: niftyMap.get(p.date) ?? initialCapital,
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-subtle text-sm">
        No NAV data yet — first run will populate this chart.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
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
            fontSize: 12,
          }}
          formatter={(value: number, name: string) => [
            formatINR(value, 0),
            name === "portfolio" ? "Portfolio NAV" : "Nifty 50 TRI",
          ]}
        />
        <Legend
          formatter={(value) =>
            value === "portfolio" ? "Portfolio NAV" : "Nifty 50 TRI"
          }
          wrapperStyle={{ color: "#94a3b8", fontSize: 12 }}
        />
        <Line
          type="monotone"
          dataKey="portfolio"
          stroke="#6366f1"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: "#6366f1" }}
        />
        <Line
          type="monotone"
          dataKey="nifty"
          stroke="#f59e0b"
          strokeWidth={1.5}
          strokeDasharray="5 3"
          dot={false}
          activeDot={{ r: 3, fill: "#f59e0b" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
