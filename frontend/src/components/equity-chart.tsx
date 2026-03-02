"use client";

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface EquityPoint {
  date: string;
  equity: number;
}

interface EquityChartProps {
  data: EquityPoint[];
  startingCapital: number;
}

const formatINRCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  } catch {
    return dateStr;
  }
}

export function EquityChart({ data, startingCapital }: EquityChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        No equity data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: "#64748b" }}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={(val: number) => formatINRCompact.format(val)}
          tick={{ fontSize: 11, fill: "#64748b" }}
          width={80}
        />
        <Tooltip
          formatter={(value: number | undefined) => [formatINRCompact.format(value ?? 0), "Equity"]}
          labelFormatter={(label: string | number | React.ReactNode) => formatDate(String(label ?? ""))}
          contentStyle={{
            backgroundColor: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
            fontSize: "12px",
          }}
        />
        <Line
          type="monotone"
          dataKey="equity"
          stroke="#0d9488"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: "#0d9488" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
