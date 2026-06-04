"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getTrades,
  getLatestStance,
  getWatchlist,
  getTradeStats,
  healthCheck,
  resetLegacyData,
  type Trade,
  type MarketStance,
  type WatchlistItem,
  type TradeStats,
  type HealthStatus,
} from "@/lib/api";
import { getRiskStatus, type RiskStatus } from "@/lib/intelligence-api";
import {
  SystemStatusBanner,
  DrawdownBanner,
  MorningCheckCards,
  OpenPositionsTable,
  WatchlistSection,
  ActionsCTA,
  PostMarketLinks,
  RsPortfolioCard,
} from "./components/dashboard-sections";

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

const V2_CUTOFF = "2025-01-01";

function LegacyDataBanner({
  openTrades,
  onReset,
}: {
  openTrades: Trade[];
  onReset: () => void;
}) {
  const [resetting, setResetting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const hasLegacy =
    openTrades.length > 0 &&
    openTrades.some((t) => (t.entry_date || "") < V2_CUTOFF);

  if (!hasLegacy && openTrades.length === 0) return null;

  // Show if there are clearly too many open positions (v2 max = 15)
  const manyOpen = openTrades.length > 15;
  const legacyDates = openTrades.some((t) => (t.entry_date || "") < V2_CUTOFF);
  if (!manyOpen && !legacyDates) return null;

  async function handleReset() {
    setResetting(true);
    setResult(null);
    try {
      const res = await resetLegacyData();
      setResult(res.message);
      onReset();
    } catch (err) {
      setResult("Reset failed: " + String(err));
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="bg-amber-50 border border-amber-300 rounded-xl px-4 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-amber-900">
            Legacy data detected — {openTrades.length} pre-v2 open trades in the database
          </p>
          <p className="text-xs text-amber-700 mt-1">
            These are old CTS trades from before the v2 migration. The v2 paper engine manages its
            own trades. Click to archive them so the dashboard reflects the correct v2 state.
          </p>
          {result && (
            <p className="text-xs text-amber-800 mt-2 font-medium">{result}</p>
          )}
        </div>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="shrink-0 text-xs font-semibold bg-amber-600 hover:bg-amber-700 disabled:bg-amber-400 text-white rounded-lg px-3 py-2 transition-colors"
        >
          {resetting ? "Archiving..." : "Archive Legacy Data"}
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [stance, setStance] = useState<MarketStance | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [risk, setRisk] = useState<RiskStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [tradesData, stanceData, watchlistData, statsData, healthData, riskData] = await Promise.allSettled([
        getTrades("OPEN"),
        getLatestStance(),
        getWatchlist(),
        getTradeStats(),
        healthCheck(),
        getRiskStatus(),
      ]);

      if (tradesData.status === "fulfilled") setOpenTrades(tradesData.value);
      if (stanceData.status === "fulfilled") setStance(stanceData.value);
      if (watchlistData.status === "fulfilled") setWatchlist(watchlistData.value);
      if (statsData.status === "fulfilled") setStats(statsData.value);
      if (healthData.status === "fulfilled") setHealth(healthData.value);
      if (riskData.status === "fulfilled") setRisk(riskData.value);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    // Re-check health every 60 s — catches if the backend goes down
    const id = setInterval(() => healthCheck().then(setHealth).catch(() => setHealth(null)), 60_000);
    return () => clearInterval(id);
  }, [fetchAll]);

  // Derived values
  const readyStocks = watchlist.filter((w) => w.bucket === "READY");
  const nearStocks = watchlist.filter((w) => w.bucket === "NEAR");
  const totalOpenRisk = openTrades.reduce((sum, t) => sum + (t.rpt_amount ?? 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">Daily command centre — Champion Trader routine</p>
      </div>

      {/* Legacy data migration banner */}
      <LegacyDataBanner openTrades={openTrades} onReset={fetchAll} />

      {/* System Status */}
      <SystemStatusBanner health={health} />

      {/* Drawdown breaker state */}
      <DrawdownBanner risk={risk} />

      {/* Morning Check */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Morning Check</h2>
          <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">15 min</span>
        </div>

        <MorningCheckCards
          openTrades={openTrades}
          totalOpenRisk={totalOpenRisk}
          stance={stance}
          stats={stats}
          loading={loading}
        />

        {!loading && <OpenPositionsTable trades={openTrades} />}
      </div>

      {/* Market Close */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Market Close</h2>
          <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">30 min</span>
        </div>

        <WatchlistSection readyStocks={readyStocks} loading={loading} />

        {readyStocks.length > 0 && <ActionsCTA />}
      </div>

      {/* Post-Market Analysis */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Post-Market Analysis</h2>
          <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">1 hour</span>
        </div>

        <PostMarketLinks
          nearCount={nearStocks.length}
          readyCount={readyStocks.length}
          stance={stance}
        />
      </div>

      {/* Strategies */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Automated Strategies</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <RsPortfolioCard />
        </div>
      </div>
    </div>
  );
}
