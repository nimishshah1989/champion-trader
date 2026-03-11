"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getTrades,
  getTradeStats,
  createTrade,
  recordPartialExit,
  closeTrade,
  type Trade,
  type TradeStats,
  type TradeCreateRequest,
} from "@/lib/api";
import { toast } from "sonner";
import { formatINR } from "@/lib/format";
import { InfoBanner, Term } from "@/components/info-banner";
import { NewTradeForm } from "./trade-form";
import { TradeRow } from "./trade-card";
import { PartialExitModal, CloseTradeModal } from "./trade-modals";
import { type StatusFilter, STATUS_FILTERS } from "./trade-helpers";
import { StatCards, TableSkeletons } from "./trades-stat-cards";

// ---------------------------------------------------------------------------
// Trades Tab — Main Content
// ---------------------------------------------------------------------------

export function TradesTab() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("ALL");
  const [showNewTradeForm, setShowNewTradeForm] = useState(false);
  const [expandedTradeId, setExpandedTradeId] = useState<number | null>(null);
  const [partialExitTrade, setPartialExitTrade] = useState<Trade | null>(null);
  const [closeTradeTarget, setCloseTradeTarget] = useState<Trade | null>(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const statusParam = activeFilter === "ALL" ? undefined : activeFilter;
      const [tradesData, statsData] = await Promise.allSettled([
        getTrades(statusParam),
        getTradeStats(),
      ]);

      if (tradesData.status === "fulfilled") {
        setTrades(tradesData.value);
      } else {
        throw tradesData.reason;
      }

      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch trades";
      setError(message);
      toast.error("Failed to load trades");
    } finally {
      setLoading(false);
    }
  }, [activeFilter]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

  async function handleCreateTrade(data: TradeCreateRequest) {
    try {
      await createTrade(data);
      toast.success(`Trade logged: ${data.symbol}`);
      setShowNewTradeForm(false);
      await fetchData();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to create trade";
      toast.error(message);
    }
  }

  async function handlePartialExit(
    tradeId: number,
    data: {
      exit_date: string;
      exit_price: number;
      exit_qty: number;
      exit_reason: string;
      notes?: string;
    },
  ) {
    try {
      const result = await recordPartialExit(tradeId, data);
      toast.success(
        `Partial exit recorded. Remaining qty: ${result.remaining_qty}`,
      );
      setPartialExitTrade(null);
      await fetchData();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to record partial exit";
      toast.error(message);
    }
  }

  async function handleCloseTrade(
    tradeId: number,
    data: {
      exit_date: string;
      exit_price: number;
      exit_reason: string;
      exit_notes?: string;
    },
  ) {
    try {
      const result = await closeTrade(tradeId, data);
      toast.success(
        `Trade closed. Gross P&L: ${formatINR.format(result.gross_pnl)}`,
      );
      setCloseTradeTarget(null);
      setExpandedTradeId(null);
      await fetchData();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to close trade";
      toast.error(message);
    }
  }

  function toggleRow(tradeId: number) {
    setExpandedTradeId((prev) => (prev === tradeId ? null : tradeId));
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header row with trade count and new trade button */}
      <div className="flex items-center justify-end gap-3">
        <span className="text-xs text-slate-400 font-mono tabular-nums">
          {trades.length} trade{trades.length !== 1 ? "s" : ""}
        </span>
        {!showNewTradeForm && (
          <button
            onClick={() => setShowNewTradeForm(true)}
            className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm flex items-center gap-1"
          >
            <span>+</span> New Trade
          </button>
        )}
      </div>

      <InfoBanner title="Quick Reference -- Trade Terms" storageKey="trades">
        <Term label="Entry Types">
          LIVE_BREAK (buy on breakout bar), CLOSE_ABOVE (buy after close
          confirms above trigger), NEXT_DAY_HIGH (buy next day above high of
          breakout bar).
        </Term>
        <Term label="R-Multiple">
          P&L as multiples of initial risk. +2R = made 2x what you risked. -1R =
          full stop-loss hit.
        </Term>
        <Term label="Exit Framework">
          2R = book 20%, NE (4x TRP) = book 20%, GE (8x TRP) = book 40%, EE
          (12x TRP) = book 80%. Remaining rides with trailing Stop Loss.
        </Term>
        <Term label="Average Risk-Reward">
          Average winning trade size divided by average losing trade size. Target
          &gt;2.0.
        </Term>
        <Term label="Status">
          OPEN (active), PARTIAL (some exits taken), CLOSED (fully exited).
        </Term>
      </InfoBanner>

      {/* New Trade Form (slide-down) */}
      {showNewTradeForm && (
        <NewTradeForm
          onSave={handleCreateTrade}
          onCancel={() => setShowNewTradeForm(false)}
        />
      )}

      {/* Stats Cards */}
      <StatCards stats={stats} loading={loading} />

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">
            Failed to load trades
          </p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchData();
            }}
            className="bg-red-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Status filter tabs + Trade table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {/* Filter Tabs */}
        <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeFilter === filter
                  ? "bg-teal-600 text-white"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        {/* Loading state */}
        {loading && <TableSkeletons />}

        {/* Empty state */}
        {!loading && !error && trades.length === 0 && (
          <div className="p-12 text-center">
            <p className="text-sm text-slate-400 mb-2">
              {activeFilter === "ALL"
                ? "No trades recorded yet."
                : `No ${activeFilter} trades found.`}
            </p>
            {activeFilter === "ALL" && (
              <button
                onClick={() => setShowNewTradeForm(true)}
                className="text-xs text-teal-600 hover:text-teal-700 font-medium mt-1"
              >
                Log your first trade
              </button>
            )}
          </div>
        )}

        {/* Trade table */}
        {!loading && !error && trades.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="px-5 py-2.5 font-medium">Symbol</th>
                  <th className="px-5 py-2.5 font-medium">Entry Date</th>
                  <th className="px-5 py-2.5 font-medium text-right">
                    Entry Price
                  </th>
                  <th className="px-5 py-2.5 font-medium text-right">Qty</th>
                  <th className="px-5 py-2.5 font-medium text-right">
                    Remaining
                  </th>
                  <th className="px-5 py-2.5 font-medium text-right">
                    Stop Loss Price
                  </th>
                  <th className="px-5 py-2.5 font-medium text-right">P&L</th>
                  <th className="px-5 py-2.5 font-medium text-right">
                    R-Multiple
                  </th>
                  <th className="px-5 py-2.5 font-medium text-center">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => {
                  const isExpanded = expandedTradeId === trade.id;
                  return (
                    <TradeRow
                      key={trade.id}
                      trade={trade}
                      isExpanded={isExpanded}
                      onToggle={() => toggleRow(trade.id)}
                      onPartialExit={() => setPartialExitTrade(trade)}
                      onCloseTrade={() => setCloseTradeTarget(trade)}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Partial Exit Modal */}
      {partialExitTrade && (
        <PartialExitModal
          trade={partialExitTrade}
          onSave={handlePartialExit}
          onClose={() => setPartialExitTrade(null)}
        />
      )}

      {/* Close Trade Modal */}
      {closeTradeTarget && (
        <CloseTradeModal
          trade={closeTradeTarget}
          onSave={handleCloseTrade}
          onClose={() => setCloseTradeTarget(null)}
        />
      )}
    </div>
  );
}
