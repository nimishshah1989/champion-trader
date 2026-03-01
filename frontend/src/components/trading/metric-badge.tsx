interface MetricBadgeProps {
  label: string;
  value: string | number;
  target?: string;
  status?: "good" | "warning" | "bad" | "neutral";
}

export function MetricBadge({ label, value, target, status = "neutral" }: MetricBadgeProps) {
  const statusColor =
    status === "good"
      ? "border-green-200 bg-green-50 text-green-700"
      : status === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : status === "bad"
          ? "border-red-200 bg-red-50 text-red-700"
          : "border-border bg-muted text-muted-foreground";

  return (
    <div className={`rounded-lg border p-3 ${statusColor}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-lg font-bold">{value}</p>
      {target && <p className="text-xs opacity-60">Target: {target}</p>}
    </div>
  );
}
