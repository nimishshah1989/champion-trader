"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getSimulationRuns,
  cleanupStuckBacktests,
  type SimulationRun,
} from "@/lib/api";
import { toast } from "sonner";
import { InfoBanner, Term } from "@/components/info-banner";
import { StatsSkeletons } from "./components/simulation-ui";
import { BacktestTab } from "./components/backtest-tab";
import { PaperTradingTab } from "./components/paper-trading-tab";

type TabType = "BACKTEST" | "PAPER";

const TABS: { key: TabType; label: string }[] = [
  { key: "BACKTEST", label: "Historical Backtest" },
  { key: "PAPER", label: "Paper Trading" },
];

export default function SimulationPage() {
  const [activeTab, setActiveTab] = useState<TabType>("BACKTEST");
  const [allRuns, setAllRuns] = useState<SimulationRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [stuckCleanedUp, setStuckCleanedUp] = useState(false);

  const fetchRuns = useCallback(async () => {
    try {
      const runs = await getSimulationRuns();
      setAllRuns(runs);

      if (!stuckCleanedUp) {
        const stuckRuns = runs.filter((r) => r.status.toUpperCase() === "RUNNING");
        if (stuckRuns.length > 0) {
          try {
            const cleanup = await cleanupStuckBacktests();
            if (cleanup.cleaned > 0) {
              toast.info(`Cleaned up ${cleanup.cleaned} stuck backtest(s) from a previous session.`);
              const updatedRuns = await getSimulationRuns();
              setAllRuns(updatedRuns);
            }
          } catch (err) {
            console.error("Failed to cleanup stuck backtests:", err);
          }
        }
        setStuckCleanedUp(true);
      }
    } catch (err) {
      console.error("Failed to fetch simulation runs:", err);
    } finally {
      setRunsLoading(false);
    }
  }, [stuckCleanedUp]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Simulation</h1>
        <p className="text-sm text-slate-500">
          Backtest and paper trade the Champion Trader methodology. AutoOptimize
          uses this same engine overnight to score parameter experiments.
        </p>
      </div>

      <InfoBanner title="Quick Reference -- Simulation Engine" storageKey="simulation">
        <Term label="Historical Backtest">
          Run the full CTS strategy against historical data for ~464 NSE stocks.
          The engine scans for PPC setups, sizes positions using your RPT%, and
          executes the complete exit framework (2R at 20%, NE at 20%, GE at 40%,
          EE at 80%). Produces equity curve, drawdown, win rate, and expectancy.
        </Term>
        <Term label="Paper Trading">
          Simulate the strategy day-by-day on live market data. Process one day
          at a time to see entries, exits, and equity progression in real time.
        </Term>
        <Term label="Used by AutoOptimize">
          The overnight optimiser runs backtests to score each parameter
          experiment. Composite score = expectancy x sqrt(trade_count) x (1 -
          max_drawdown). 10 experiments per session, capped to limit compute.
        </Term>
        <Term label="Equity Curve">
          Daily portfolio value plot. Upward slope = strategy edge is working.
          Deep drawdowns indicate struggles in certain market regimes.
        </Term>
        <Term label="Key Metrics">
          Win Rate (% of profitable trades), Expectancy (expected R per trade),
          ARR (Average Risk:Reward ratio), Max Drawdown (worst peak-to-trough).
        </Term>
      </InfoBanner>

      <div className="flex items-center gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-teal-600 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {runsLoading ? (
        <StatsSkeletons count={4} />
      ) : activeTab === "BACKTEST" ? (
        <BacktestTab allRuns={allRuns} onRunsUpdated={fetchRuns} />
      ) : (
        <PaperTradingTab allRuns={allRuns} onRunsUpdated={fetchRuns} />
      )}
    </div>
  );
}
