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
  type ScanResult,
  type WatchlistItem,
} from "@/lib/api";
import { ScanControls } from "./components/scan-controls";
import { PipelineKanban, type AddStockFormData } from "./components/pipeline-kanban";
import { PipelineLearn } from "./components/pipeline-learn";
import {
  type ScanType,
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
  const [scanType, setScanType] = useState<ScanType>("ALL");
  const [scanDate, setScanDate] = useState(getTodayISO());
  const [isScanning, setIsScanning] = useState(false);

  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([]);

  const [loadingScan, setLoadingScan] = useState(true);
  const [loadingWatchlist, setLoadingWatchlist] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [hasScanned, setHasScanned] = useState(false);

  const [updatingSymbols, setUpdatingSymbols] = useState<Set<string>>(new Set());

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
      ppc: scanResults.filter((r) => r.scan_type === "PPC").length,
      npc: scanResults.filter((r) => r.scan_type === "NPC").length,
      contraction: scanResults.filter((r) => r.scan_type === "CONTRACTION").length,
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
    } catch {
      // No cached results — acceptable on first visit
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

  useEffect(() => {
    fetchLatestScan();
    fetchWatchlist();
  }, [fetchLatestScan, fetchWatchlist]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  async function handleRunScan() {
    setIsScanning(true);
    try {
      const data = await runScan({ scan_type: scanType, date: scanDate });
      setScanResults(data);
      setHasScanned(true);
      toast.success(`Scan complete -- ${data.length} signals found`);
      // Auto-add qualifying results to watchlist
      await autoPopulateWatchlist(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Scan failed";
      toast.error(message);
    } finally {
      setIsScanning(false);
    }
  }

  /**
   * After a scan, automatically add qualifying results to the watchlist
   * so they persist across sessions. Skip symbols already in the watchlist.
   */
  async function autoPopulateWatchlist(results: ScanResult[]) {
    const existingSymbols = new Set(watchlistItems.map((w) => w.symbol));
    const toAdd = results.filter(
      (r) => !existingSymbols.has(r.symbol) && r.watchlist_bucket,
    );

    if (toAdd.length === 0) return;

    let addedCount = 0;
    for (const result of toAdd) {
      try {
        await addToWatchlist({
          symbol: result.symbol,
          bucket: result.watchlist_bucket || "AWAY",
          stage: result.stage || undefined,
          trigger_level: result.trigger_level || undefined,
          planned_sl_pct: result.trp || undefined,
          wuc_types: result.wuc_type || undefined,
          notes: `Auto-added from ${result.scan_type} scan on ${result.scan_date}`,
        });
        addedCount++;
      } catch {
        // Individual add failure is non-blocking
      }
    }

    if (addedCount > 0) {
      toast.success(`${addedCount} new stock${addedCount > 1 ? "s" : ""} auto-added to pipeline`);
      await fetchWatchlist();
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
          planned_sl_pct: scanItem?.trp || undefined,
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
          Scan for patterns, auto-categorize into READY / NEAR / AWAY, and track stocks toward entry
        </p>
      </div>

      {/* Scan controls */}
      <ScanControls
        scanType={scanType}
        onScanTypeChange={setScanType}
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
            Run your first scan to detect Positive Pivotal Candle, Negative Pivotal Candle,
            and Base Contraction patterns across ~500 stocks. Qualifying results will
            automatically populate into the board below. Best run after market close
            (3:30 PM IST).
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
