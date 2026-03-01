import { Badge } from "@/components/ui/badge";

interface TradeRowProps {
  symbol: string;
  entryDate: string;
  avgEntryPrice: number;
  totalQty: number;
  slPrice: number;
  status: string;
  grossPnl?: number;
  rMultiple?: number;
  pnlPct?: number;
}

export function TradeRow({
  symbol,
  entryDate,
  avgEntryPrice,
  totalQty,
  slPrice,
  status,
  grossPnl,
  rMultiple,
  pnlPct,
}: TradeRowProps) {
  const statusVariant =
    status === "OPEN"
      ? "default"
      : status === "PARTIAL"
        ? "secondary"
        : "outline";

  const pnlColor =
    grossPnl !== undefined
      ? grossPnl > 0
        ? "text-green-600"
        : grossPnl < 0
          ? "text-red-600"
          : ""
      : "";

  return (
    <tr className="border-b text-sm">
      <td className="py-2 font-medium">{symbol}</td>
      <td className="py-2">{entryDate}</td>
      <td className="py-2 font-mono">{avgEntryPrice.toFixed(2)}</td>
      <td className="py-2">{totalQty}</td>
      <td className="py-2 font-mono text-red-600">{slPrice.toFixed(2)}</td>
      <td className="py-2">
        <Badge variant={statusVariant}>{status}</Badge>
      </td>
      <td className={`py-2 font-mono ${pnlColor}`}>
        {grossPnl !== undefined ? `${grossPnl > 0 ? "+" : ""}${grossPnl.toFixed(2)}` : "—"}
      </td>
      <td className={`py-2 font-mono ${pnlColor}`}>
        {rMultiple !== undefined ? `${rMultiple > 0 ? "+" : ""}${rMultiple.toFixed(2)}R` : "—"}
      </td>
    </tr>
  );
}
