"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getTrades,
  getLatestStance,
  getWatchlist,
  getTradeStats,
  healthCheck,
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
} from "./components/dashboard-sections";

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

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
    </div>
  );
}
