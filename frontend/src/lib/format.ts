// ---------------------------------------------------------------------------
// Shared INR formatting utilities
// Used across Pipeline, Actions, Trades, Dashboard, and Settings pages
// ---------------------------------------------------------------------------

const CRORE = 10_000_000;
const LAKH = 100_000;

/** Full INR format with 2 decimal places: ₹1,234.56 */
export const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

/** Compact INR format with no decimals: ₹1,235 */
export const formatINRCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

/** Human-readable Indian notation: ₹5.00 L or ₹1.50 Cr */
export function formatIndian(n: number): string {
  if (n >= CRORE) return `\u20B9${(n / CRORE).toFixed(2)} Cr`;
  if (n >= LAKH) return `\u20B9${(n / LAKH).toFixed(2)} L`;
  return `\u20B9${n.toLocaleString("en-IN")}`;
}

/** INR value string: ₹1,234.56 (function form for pipeline compatibility) */
export function formatINRValue(value: number): string {
  return formatINR.format(value);
}

/** Format lakhs/crores display for large values */
export function formatLakhs(value: number): string {
  if (value >= CRORE) return `${(value / CRORE).toFixed(2)} Cr`;
  if (value >= LAKH) return `${(value / LAKH).toFixed(2)}L`;
  return formatINRCompact.format(value);
}

/** Format a date string to Indian locale short format */
export function formatDateShort(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

/** Today's date as YYYY-MM-DD */
export function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

/** Safe number formatting — returns fallback for null/undefined values */
export function safeFixed(val: number | null | undefined, digits: number, fallback = "--"): string {
  return val != null ? val.toFixed(digits) : fallback;
}

/** Safe INR formatting — returns fallback for null/undefined values */
export function safeFormatINR(val: number | null | undefined, fallback = "--"): string {
  return val != null ? formatINR.format(val) : fallback;
}
