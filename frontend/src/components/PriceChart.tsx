"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PriceSeries } from "@/lib/api";

const COLORS = [
  "#3B4CCA", // Pokémon blue
  "#CC0000", // Pokémon red
  "#16a34a", // green
  "#b59800", // yellow-dark
  "#0ea5e9", // sky blue
  "#7c3aed", // violet
];

export function PriceChart({ series }: { series: PriceSeries[] }) {
  const byDate = new Map<string, Record<string, number | string>>();
  for (const s of series) {
    for (const p of s.points) {
      const day = p.recorded_at.slice(0, 10);
      const row = byDate.get(day) ?? { date: day };
      row[s.store_name] = p.sale_price ?? p.price;
      byDate.set(day, row);
    }
  }
  const data = [...byDate.values()].sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );

  if (data.length === 0)
    return (
      <p className="text-center text-sm text-ink-3 py-8">Sin historial todavía.</p>
    );

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef1ff" />
        <XAxis
          dataKey="date"
          stroke="#c5cfe8"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
        />
        <YAxis
          stroke="#c5cfe8"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
          width={48}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#ffffff",
            border: "2px solid #dde3f0",
            borderRadius: "12px",
            fontSize: 12,
            color: "#1a1a3e",
            boxShadow: "0 4px 16px rgba(59,76,202,0.1)",
          }}
          labelStyle={{ color: "#4a5270", marginBottom: 4, fontWeight: 600 }}
          formatter={(value: number) => [`$${value.toLocaleString("es-CL")}`, ""]}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: "#4a5270", paddingTop: 12 }}
        />
        {series.map((s, i) => (
          <Line
            key={s.listing_id}
            type="stepAfter"
            dataKey={s.store_name}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2.5}
            dot={false}
            connectNulls
            activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
