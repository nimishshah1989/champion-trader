"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  runScan,
  getLatestScanResults,
  addToWatchlist,
  type ScanResult,
} from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

type ScanType = "PPC" | "NPC" | "CONTRACTION" | "ALL";

const SCAN_TYPES: { value: ScanType; label: string; description: string }[] = [
  { value: "ALL", label: "All Scans", description: "PPC + NPC + Contraction" },
  { value: "PPC", label: "PPC", description: "Positive Pivotal Candle" },
  { value: "NPC", label: "NPC", description: "Negative Pivotal Candle" },
  { value: "CONTRACTION", label: "Contraction", description: "Base Contraction" },
];

const SCAN_TYPE_META: Record<
  string,
  { label: string; color: string; headerBg: string; borderColor: string; icon: string; emptyText: string }
> = {
  PPC: {
    label: "PPC",
    color: "text-emerald-700",
    headerBg: "bg-emerald-50",
    borderColor: "border-emerald-200",
    icon: "▲",
    emptyText: "No PPC signals detected for this date.",
  },
  NPC: {
    label: "NPC",
    color: "text-red-700",
    headerBg: "bg-red-50",
    borderColor: "border-red-200",
    icon: "▼",
    emptyText: "No NPC signals detected for this date.",
  },
  CONTRACTION: {
    label: "Contraction",
    color: "text-blue-700",
    headerBg: "bg-blue-50",
    borderColor: "border-blue-200",
    icon: "◆",
    emptyText: "No contraction patterns detected for this date.",
  },
};

const STAGE_COLORS: Record<string, string> = {
  S1: "bg-slate-100 text-slate-600",
  S1B: "bg-teal-100 text-teal-700",
  S2: "bg-blue-100 text-blue-700",
  S3: "bg-amber-100 text-amber-700",
  S4: "bg-red-100 text-red-700",
  UNKNOWN: "bg-slate-100 text-slate-500",
};

const BUCKET_COLORS: Record<string, string> = {
  READY: "bg-emerald-100 text-emerald-700",
  NEAR: "bg-amber-100 text-amber-700",
  AWAY: "bg-blue-100 text-blue-700",
};

const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatADT(adt: number | null): string {
  if (adt === null || adt === 0) return "-";
  if (adt >= 1_00_00_000) return `${(adt / 1_00_00_000).toFixed(1)} Cr`;
  if (adt >= 1_00_000) return `${(adt / 1_00_000).toFixed(1)} L`;
  return `${(adt / 1000).toFixed(0)}K`;
}

function getTodayISO(): string {
  return new Date().toISOString().split("T")[0];
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ScanControlBar({
  scanType,
  onScanTypeChange,
  scanDate,
  onDateChange,
  onRunScan,
  isScanning,
}: {
  scanType: ScanType;
  onScanTypeChange: (t: ScanType) => void;
  scanDate: string;
  onDateChange: (d: string) => void;
  onRunScan: () => void;
  isScanning: boolean;
}) {
  const inputClass =
    "bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-end gap-4">
        {/* Scan Type */}
        <div>
          <label className="text-xs text-slate-500 mb-1 block font-medium">
            Scan Type
          </label>
          <select
            className={inputClass}
            value={scanType}
            onChange={(e) => onScanTypeChange(e.target.value as ScanType)}
            disabled={isScanning}
          >
            {SCAN_TYPES.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label} — {st.description}
              </option>
            ))}
          </select>
        </div>

        {/* Scan Date */}
        <div>
          <label className="text-xs text-slate-500 mb-1 block font-medium">
            Scan Date
          </label>
          <input
            type="date"
            className={inputClass}
            value={scanDate}
            onChange={(e) => onDateChange(e.target.value)}
            disabled={isScanning}
            max={getTodayISO()}
          />
        </div>

        {/* Run Button */}
        <button
          onClick={onRunScan}
          disabled={isScanning}
          className="bg-teal-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
        >
          {isScanning ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Scanning...
            </>
          ) : (
            <>Run Scan</>
          )}
        </button>
      </div>

      {isScanning && (
        <div className="mt-3 bg-teal-50 border border-teal-200 rounded-lg px-4 py-3">
          <p className="text-sm text-teal-700 font-medium">
            Scanning ~200 NIFTY stocks... this takes 1-2 minutes
          </p>
          <p className="text-xs text-teal-600 mt-1">
            Downloading price data in batches, then running PPC/NPC/Contraction detection.
          </p>
        </div>
      )}
    </div>
  );
}

function ColumnSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
          <Skeleton className="h-5 w-24 bg-slate-100" />
          <Skeleton className="h-4 w-32 bg-slate-100" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-12 bg-slate-100 rounded-full" />
            <Skeleton className="h-5 w-14 bg-slate-100 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

function StageBadge({ stage }: { stage: string | null }) {
  if (!stage) return null;
  const color = STAGE_COLORS[stage] || "bg-slate-100 text-slate-500";
  return (
    <span className={`${color} rounded-full px-2 py-0.5 text-[11px] font-semibold`}>
      {stage}
    </span>
  );
}

function BucketBadge({ bucket }: { bucket: string | null }) {
  if (!bucket) return null;
  const color = BUCKET_COLORS[bucket] || "bg-slate-100 text-slate-500";
  return (
    <span className={`${color} rounded-full px-2 py-0.5 text-[11px] font-semibold`}>
      {bucket}
    </span>
  );
}

function ResultCard({
  result,
  onAddToWatchlist,
  isAdding,
}: {
  result: ScanResult;
  onAddToWatchlist: (result: ScanResult) => void;
  isAdding: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-colors">
      {/* Header: Symbol + Stage + Bucket */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-slate-800 tracking-wide">
          {result.symbol}
        </span>
        <div className="flex items-center gap-1.5">
          <StageBadge stage={result.stage} />
          <BucketBadge bucket={result.watchlist_bucket} />
        </div>
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mb-3">
        <div>
          <span className="text-slate-400">Close</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">
            {result.close_price !== null ? formatINR.format(result.close_price) : "-"}
          </span>
        </div>
        <div>
          <span className="text-slate-400">TRP Ratio</span>
          <span className={`ml-1 font-mono font-semibold ${
            result.trp_ratio !== null && result.trp_ratio >= 2.0
              ? "text-emerald-600"
              : result.trp_ratio !== null && result.trp_ratio >= 1.5
                ? "text-teal-600"
                : "text-slate-700"
          }`}>
            {result.trp_ratio !== null ? `${result.trp_ratio}x` : "-"}
          </span>
        </div>
        <div>
          <span className="text-slate-400">Vol Ratio</span>
          <span className={`ml-1 font-mono font-semibold ${
            result.volume_ratio !== null && result.volume_ratio >= 2.0
              ? "text-emerald-600"
              : result.volume_ratio !== null && result.volume_ratio >= 1.5
                ? "text-teal-600"
                : "text-slate-700"
          }`}>
            {result.volume_ratio !== null ? `${result.volume_ratio}x` : "-"}
          </span>
        </div>
        <div>
          <span className="text-slate-400">ADT</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">
            {formatADT(result.adt)}
          </span>
        </div>
        {result.base_days !== null && result.base_days > 0 && (
          <div>
            <span className="text-slate-400">Base</span>
            <span className="ml-1 font-mono font-semibold text-slate-700">
              {result.base_days}d
            </span>
            {result.base_quality && result.base_quality !== "UNKNOWN" && (
              <span className="ml-1 text-slate-500">
                ({result.base_quality})
              </span>
            )}
          </div>
        )}
        {result.trigger_level !== null && (
          <div>
            <span className="text-slate-400">Trigger</span>
            <span className="ml-1 font-mono font-semibold text-emerald-600">
              {formatINR.format(result.trigger_level)}
            </span>
          </div>
        )}
      </div>

      {/* Extra: Close position bar for PPC/NPC */}
      {result.close_position !== null && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-0.5">
            <span>Close Position</span>
            <span className="font-mono">{(result.close_position * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                result.close_position >= 0.6
                  ? "bg-emerald-500"
                  : result.close_position <= 0.4
                    ? "bg-red-500"
                    : "bg-amber-400"
              }`}
              style={{ width: `${Math.min(result.close_position * 100, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button
          onClick={() => onAddToWatchlist(result)}
          disabled={isAdding}
          className="text-[11px] font-medium px-2.5 py-1 rounded border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors disabled:opacity-50"
        >
          + Watchlist
        </button>
        <Link
          href={`/calculator?symbol=${encodeURIComponent(result.symbol)}${
            result.trigger_level ? `&entry_price=${result.trigger_level}` : ""
          }${result.trp ? `&trp_pct=${result.trp}` : ""}`}
          className="text-[11px] font-medium px-2.5 py-1 rounded border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition-colors"
        >
          Calculate
        </Link>
      </div>
    </div>
  );
}

function EmptyColumn({ scanType }: { scanType: string }) {
  const meta = SCAN_TYPE_META[scanType];
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
      <div className="text-2xl mb-2 text-slate-300">{meta?.icon || "—"}</div>
      <p className="text-sm text-slate-400">{meta?.emptyText || "No results."}</p>
    </div>
  );
}

function ScanSummaryBar({ results }: { results: ScanResult[] }) {
  const ppcCount = results.filter((r) => r.scan_type === "PPC").length;
  const npcCount = results.filter((r) => r.scan_type === "NPC").length;
  const contractionCount = results.filter((r) => r.scan_type === "CONTRACTION").length;
  const scanDate = results[0]?.scan_date;

  return (
    <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex flex-wrap items-center gap-4">
      <div className="text-xs text-slate-500">
        <span className="font-medium text-slate-700">
          {results.length} signals found
        </span>
        {scanDate && (
          <span className="ml-2">
            for {new Date(scanDate).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 ml-auto">
        <span className="text-xs font-mono">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />
          PPC: {ppcCount}
        </span>
        <span className="text-xs font-mono">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />
          NPC: {npcCount}
        </span>
        <span className="text-xs font-mono">
          <span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />
          Contraction: {contractionCount}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ScannerPage() {
  const [scanType, setScanType] = useState<ScanType>("ALL");
  const [scanDate, setScanDate] = useState(getTodayISO());
  const [results, setResults] = useState<ScanResult[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [addingSymbols, setAddingSymbols] = useState<Set<string>>(new Set());
  const [hasScanned, setHasScanned] = useState(false);

  // Load latest results on mount
  const fetchLatest = useCallback(async () => {
    try {
      const data = await getLatestScanResults();
      if (data.length > 0) {
        setResults(data);
        setHasScanned(true);
        // Set scan date to match the latest results
        if (data[0]?.scan_date) {
          setScanDate(data[0].scan_date);
        }
      }
    } catch {
      // No cached results — that's fine
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLatest();
  }, [fetchLatest]);

  // Run scan
  async function handleRunScan() {
    setIsScanning(true);
    try {
      const data = await runScan({ scan_type: scanType, date: scanDate });
      setResults(data);
      setHasScanned(true);
      toast.success(`Scan complete — ${data.length} signals found`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Scan failed";
      toast.error(message);
    } finally {
      setIsScanning(false);
    }
  }

  // Add to watchlist from scan result
  async function handleAddToWatchlist(result: ScanResult) {
    setAddingSymbols((prev) => new Set(prev).add(result.symbol));
    try {
      await addToWatchlist({
        symbol: result.symbol,
        bucket: result.watchlist_bucket || "AWAY",
        stage: result.stage || undefined,
        trigger_level: result.trigger_level || undefined,
        wuc_types: result.wuc_type || undefined,
        notes: `Added from ${result.scan_type} scan on ${result.scan_date}`,
      });
      toast.success(`${result.symbol} added to ${result.watchlist_bucket || "AWAY"} watchlist`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to add to watchlist";
      toast.error(message);
    } finally {
      setAddingSymbols((prev) => {
        const next = new Set(prev);
        next.delete(result.symbol);
        return next;
      });
    }
  }

  // Group results by scan type
  const ppcResults = results.filter((r) => r.scan_type === "PPC");
  const npcResults = results.filter((r) => r.scan_type === "NPC");
  const contractionResults = results.filter((r) => r.scan_type === "CONTRACTION");

  const columnData: { type: string; results: ScanResult[] }[] = [
    { type: "PPC", results: ppcResults },
    { type: "NPC", results: npcResults },
    { type: "CONTRACTION", results: contractionResults },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Scanner</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Run PPC, NPC, and Contraction scans on NIFTY 200 stocks — post-market daily
        </p>
      </div>

      {/* Scan controls */}
      <ScanControlBar
        scanType={scanType}
        onScanTypeChange={setScanType}
        scanDate={scanDate}
        onDateChange={setScanDate}
        onRunScan={handleRunScan}
        isScanning={isScanning}
      />

      {/* Summary bar */}
      {!isScanning && results.length > 0 && <ScanSummaryBar results={results} />}

      {/* Initial loading state */}
      {isLoading && !isScanning && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-12 w-full bg-slate-100 rounded-xl" />
              <ColumnSkeleton />
            </div>
          ))}
        </div>
      )}

      {/* No results yet — first-time user experience */}
      {!isLoading && !isScanning && !hasScanned && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-3 text-slate-200">&#9906;</div>
          <h3 className="text-sm font-semibold text-slate-700 mb-1">No scan results yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Run your first scan to detect PPC, NPC, and Contraction patterns across NIFTY 200
            stocks. Best run after market close (3:30 PM IST).
          </p>
        </div>
      )}

      {/* Results — 3-column grid */}
      {!isLoading && !isScanning && hasScanned && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {columnData.map(({ type, results: columnResults }) => {
            const meta = SCAN_TYPE_META[type];
            return (
              <div key={type} className="space-y-3">
                {/* Column header */}
                <div
                  className={`${meta.headerBg} ${meta.borderColor} border rounded-xl px-4 py-3 flex items-center justify-between`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${meta.color}`}>
                      {meta.icon} {meta.label}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      ({columnResults.length})
                    </span>
                  </div>
                </div>

                {/* Empty state */}
                {columnResults.length === 0 && <EmptyColumn scanType={type} />}

                {/* Result cards */}
                {columnResults.map((result) => (
                  <ResultCard
                    key={`${result.symbol}-${result.scan_type}`}
                    result={result}
                    onAddToWatchlist={handleAddToWatchlist}
                    isAdding={addingSymbols.has(result.symbol)}
                  />
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
