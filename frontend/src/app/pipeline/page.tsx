"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { toast } from "sonner";
import { useSettings } from "@/contexts/settings-context";
import {
  runScan,
  getLatestScanResults,
  getWatchlist,
  addToWatchlist,
  updateWatchlistItem,
  removeFromWatchlist,
  getBarStoreStatus,
  runKiteIngest,
  type ScanResult,
  type WatchlistItem,
} from "@/lib/api";
import { ScanControls } from "./components/scan-controls";
import { PipelineKanban, type AddStockFormData } from "./components/pipeline-kanban";
import { PipelineLearn } from "./components/pipeline-learn";
import {
  type Bucket,
  getTodayISO,
  mergeScanAndWatchlist,
} from "./components/pipeline-types";

// ---------------------------------------------------------------------------
// Pipeline Page — unified scanner + watchlist kanban board
// ---------------------------------------------------------------------------

export default function PipelinePage() {
  const { settings, effectiveRpt } = useSettings();

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [scanDate, setScanDate] = useState(getTodayISO());
  const [isScanning, setIsScanning] = useState(false);

  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([]);

  const [loadingScan, setLoadingScan] = useState(true);
  const [loadingWatchlist, setLoadingWatchlist] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [hasScanned, setHasScanned] = useState(false);

  const [updatingSymbols, setUpdatingSymbols] = useState<Set<string>>(new Set());

  // Bar store state
  const [barStoreSymbols, setBarStoreSymbols] = useState<number | null>(null);
  const [barStoreDate, setBarStoreDate] = useState<string | null>(null);
  const [ingestRunning, setIngestRunning] = useState(false);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  const isLoading = loadingScan || loadingWatchlist;

  const pipelineCards = useMemo(
    () =>
      mergeScanAndWatchlist(
        scanResults,
        watchlistItems,
        settings.accountValue,
        effectiveRpt,
      ),
    [scanResults, watchlistItems, settings.accountValue, effectiveRpt],
  );

  const resultCounts = useMemo(() => {
    if (scanResults.length === 0) return null;
    return {
      total: scanResults.length,
      s1b: scanResults.filter((r) => r.stage === "S1B").length,
      s2: scanResults.filter((r) => r.stage === "S2").length,
    };
  }, [scanResults]);

  const scanDateLabel = useMemo(() => {
    const dateStr = scanResults[0]?.scan_date;
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }, [scanResults]);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  const fetchLatestScan = useCallback(async () => {
    try {
      const data = await getLatestScanResults();
      if (data.length > 0) {
        setScanResults(data);
        setHasScanned(true);
        if (data[0]?.scan_date) {
          setScanDate(data[0].scan_date);
        }
      }
    } catch (err) {
      console.error("Failed to fetch latest scan results:", err);
    } finally {
      setLoadingScan(false);
    }
  }, []);

  const fetchWatchlist = useCallback(async () => {
    try {
      setWatchlistError(null);
      const data = await getWatchlist();
      setWatchlistItems(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch watchlist";
      setWatchlistError(message);
    } finally {
      setLoadingWatchlist(false);
    }
  }, []);

  const fetchBarStoreStatus = useCallback(async () => {
    try {
      const s = await getBarStoreStatus();
      setBarStoreSymbols(s.symbols_with_bars);
      setBarStoreDate(s.latest_bar_date);
    } catch {
      // silent — bar store might not be set up yet
    }
  }, []);

  useEffect(() => {
    fetchLatestScan();
    fetchWatchlist();
    fetchBarStoreStatus();
  }, [fetchLatestScan, fetchWatchlist, fetchBarStoreStatus]);

  // Poll bar store status while ingest is running
  useEffect(() => {
    if (!ingestRunning) return;
    const id = setInterval(fetchBarStoreStatus, 8_000);
    return () => clearInterval(id);
  }, [ingestRunning, fetchBarStoreStatus]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  async function handleRunScan() {
    setIsScanning(true);
    try {
      const data = await runScan({ scan_type: "V2", date: scanDate });
      setScanResults(data);
      setHasScanned(true);
      toast.success(`Scan complete -- ${data.length} v2 setup${data.length === 1 ? "" : "s"} found`);
      // The v2 scan persists ScanResult rows AND populates the watchlist server-side
      // (live_jobs.run_daily_scan), so just refresh the board from the watchlist.
      await fetchWatchlist();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Scan failed";
      toast.error(message);
    } finally {
      setIsScanning(false);
    }
  }

  async function handleMove(symbol: string, watchlistId: number | null, newBucket: Bucket) {
    setUpdatingSymbols((prev) => new Set(prev).add(symbol));
    try {
      if (watchlistId) {
        await updateWatchlistItem(watchlistId, { bucket: newBucket });
        toast.success(`${symbol} moved to ${newBucket}`);
        await fetchWatchlist();
      } else {
        // Item from scan results only; persist it first
        const scanItem = scanResults.find((r) => r.symbol === symbol);
        await addToWatchlist({
          symbol,
          bucket: newBucket,
          stage: scanItem?.stage || undefined,
          trigger_level: scanItem?.trigger_level || undefined,
          planned_sl_pct: scanItem?.avg_trp ?? scanItem?.trp ?? undefined,
          wuc_types: scanItem?.wuc_type || undefined,
          notes: scanItem
            ? `Added from ${scanItem.scan_type} scan on ${scanItem.scan_date}`
            : undefined,
        });
        toast.success(`${symbol} saved to ${newBucket}`);
        await fetchWatchlist();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to move stock";
      toast.error(message);
    } finally {
      setUpdatingSymbols((prev) => {
        const next = new Set(prev);
        next.delete(symbol);
        return next;
      });
    }
  }

  async function handleRemove(symbol: string, watchlistId: number | null) {
    setUpdatingSymbols((prev) => new Set(prev).add(symbol));
    try {
      if (watchlistId) {
        await removeFromWatchlist(watchlistId);
        toast.success(`${symbol} removed`);
        await fetchWatchlist();
      } else {
        // Remove from local scan results only
        setScanResults((prev) => prev.filter((r) => r.symbol !== symbol));
        toast.success(`${symbol} removed from scan results`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to remove stock";
      toast.error(message);
    } finally {
      setUpdatingSymbols((prev) => {
        const next = new Set(prev);
        next.delete(symbol);
        return next;
      });
    }
  }

  async function handleAddStock(data: AddStockFormData) {
    try {
      const payload: Parameters<typeof addToWatchlist>[0] = {
        symbol: data.symbol.trim(),
        bucket: data.bucket,
      };
      if (data.stage) payload.stage = data.stage;
      if (data.triggerLevel) payload.trigger_level = parseFloat(data.triggerLevel);
      if (data.trpPct) payload.planned_sl_pct = parseFloat(data.trpPct);
      if (data.notes) payload.notes = data.notes;

      await addToWatchlist(payload);
      toast.success(`${payload.symbol} added to ${payload.bucket}`);
      await fetchWatchlist();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to add stock";
      toast.error(message);
    }
  }

  async function handleRunIngest() {
    setIngestRunning(true);
    setIngestMessage(null);
    try {
      const res = await runKiteIngest(true);
      setIngestMessage(res.message);
    } catch (err) {
      setIngestMessage("Ingest failed: " + String(err));
      setIngestRunning(false);
    }
    // ingestRunning stays true until bar store shows progress via polling
    // Auto-stop after 15 minutes as a safety valve
    setTimeout(() => setIngestRunning(false), 15 * 60 * 1000);
  }

  function handleRetry() {
    setLoadingWatchlist(true);
    setLoadingScan(true);
    fetchLatestScan();
    fetchWatchlist();
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
          Pipeline
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Scan for v2 setups, auto-categorize into READY / NEAR / AWAY, and track stocks toward entry
        </p>
      </div>

      {/* Bar store status + ingest trigger */}
      {barStoreSymbols !== null && barStoreSymbols === 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl px-4 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-amber-900">Kite bar store is empty — ingest required before scanning</p>
              <p className="text-xs text-amber-700 mt-1">
                The v2 scanner reads from a local SQLite bar store populated by the Kite API.
                Since Kite is now authorized, click to fetch the last 18 months of OHLCV data for all 1 300 NSE symbols (~7 min).
              </p>
              {ingestMessage && (
                <p className="text-xs text-amber-800 mt-2 font-medium truncate">{ingestMessage}</p>
              )}
            </div>
            <button
              onClick={handleRunIngest}
              disabled={ingestRunning}
              className="shrink-0 text-xs font-semibold bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 text-white rounded-lg px-3 py-2 transition-colors"
            >
              {ingestRunning ? "Ingesting..." : "Run Ingest Now"}
            </button>
          </div>
        </div>
      )}

      {barStoreSymbols !== null && barStoreSymbols > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wide font-medium">Bar Store</p>
              <p className="text-sm font-semibold text-slate-800">{barStoreSymbols.toLocaleString()} symbols</p>
            </div>
            {barStoreDate && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wide font-medium">Latest Bar</p>
                <p className="text-sm font-semibold text-slate-800">
                  {new Date(barStoreDate).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                </p>
              </div>
            )}
          </div>
          <button
            onClick={handleRunIngest}
            disabled={ingestRunning}
            className="text-xs text-teal-600 hover:text-teal-700 disabled:text-slate-400 font-medium transition-colors"
          >
            {ingestRunning ? "Updating..." : "Refresh Bars"}
          </button>
        </div>
      )}

      {/* Scan controls */}
      <ScanControls
        scanDate={scanDate}
        onDateChange={setScanDate}
        onRunScan={handleRunScan}
        isScanning={isScanning}
        resultCounts={resultCounts}
        scanDateLabel={scanDateLabel}
      />

      {/* No results yet — first-time experience */}
      {!isLoading && !isScanning && !hasScanned && watchlistItems.length === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-3 text-slate-200">&#9906;</div>
          <h3 className="text-sm font-semibold text-slate-700 mb-1">
            Your pipeline is empty
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Run your first scan to detect validated v2 breakout setups (Stage-2 uptrend +
            volatility contraction + avg TRP &ge; 2) across the liquid NSE universe, read
            from the Kite-adjusted bar store. READY setups auto-populate the board below.
            Best run after market close.
          </p>
        </div>
      )}

      {/* Kanban board */}
      {(isLoading || hasScanned || watchlistItems.length > 0) && (
        <PipelineKanban
          cards={pipelineCards}
          loading={isLoading}
          error={watchlistError}
          onMove={handleMove}
          onRemove={handleRemove}
          updatingSymbols={updatingSymbols}
          onRetry={handleRetry}
          onAddStock={handleAddStock}
        />
      )}

      {/* Learn section */}
      <PipelineLearn />
    </div>
  );
}
