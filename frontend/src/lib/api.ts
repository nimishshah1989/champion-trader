// ---------------------------------------------------------------------------
// API Client — fetch helpers and endpoint functions
// Types are defined in ./api-types.ts and re-exported here for consumers.
// ---------------------------------------------------------------------------

import type { RequestOptions } from "./api-types";

export type {
  ScanResult,
  PositionCalcRequest,
  PositionCalcResponse,
  WatchlistItem,
  Trade,
  TradeStats,
  TradeCreateRequest,
  MarketStance,
  Journal,
  JournalCreateRequest,
  AppAlert,
  ActionAlert,
  PriceCheckResponse,
  SimulationRun,
  SimulationTrade,
  SimulationRunWithTrades,
  BacktestProgress,
  ScheduledJob,
  HealthStatus,
  RsPortfolioStatus,
  RsStrategyTrade,
  RsStrategyStatusResponse,
  RsStrategyTradesResponse,
  RsRunNowResult,
} from "./api-types";

import type {
  ScanResult,
  PositionCalcRequest,
  PositionCalcResponse,
  WatchlistItem,
  Trade,
  TradeStats,
  TradeCreateRequest,
  MarketStance,
  Journal,
  JournalCreateRequest,
  AppAlert,
  ActionAlert,
  PriceCheckResponse,
  SimulationRun,
  SimulationTrade,
  SimulationRunWithTrades,
  BacktestProgress,
  HealthStatus,
  RsPortfolioStatus,
  RsStrategyTrade,
  RsStrategyStatusResponse,
  RsStrategyTradesResponse,
  RsRunNowResult,
} from "./api-types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json() as Promise<T>;
}

// --- Scanner ---

export function runScan(data: { scan_type: string; date?: string }): Promise<ScanResult[]> {
  return apiFetch<ScanResult[]>("/scanner/run", { method: "POST", body: data });
}

export function getScanResults(scanDate?: string, scanType?: string): Promise<ScanResult[]> {
  const params = new URLSearchParams();
  if (scanDate) params.set("scan_date", scanDate);
  if (scanType) params.set("scan_type", scanType);
  const query = params.toString();
  return apiFetch<ScanResult[]>(`/scanner/results${query ? `?${query}` : ""}`);
}

export function getLatestScanResults(): Promise<ScanResult[]> {
  return apiFetch<ScanResult[]>("/scanner/results/latest");
}

// --- Position Calculator ---

export function calculatePosition(data: PositionCalcRequest): Promise<PositionCalcResponse> {
  return apiFetch<PositionCalcResponse>("/calculator/position", {
    method: "POST",
    body: data,
  });
}

// --- Watchlist ---

export function getWatchlist(): Promise<WatchlistItem[]> {
  return apiFetch<WatchlistItem[]>("/watchlist");
}

export function addToWatchlist(data: {
  symbol: string;
  bucket: string;
  stage?: string;
  trigger_level?: number;
  planned_sl_pct?: number;
  wuc_types?: string;
  notes?: string;
}): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>("/watchlist/add", { method: "POST", body: data });
}

export function updateWatchlistItem(
  id: number,
  data: {
    bucket?: string;
    trigger_level?: number;
    planned_entry_price?: number;
    planned_sl_pct?: number;
    planned_position_size?: number;
    planned_half_qty?: number;
    status?: string;
    removed_reason?: string;
    notes?: string;
  },
): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>(`/watchlist/${id}`, { method: "PATCH", body: data });
}

export function removeFromWatchlist(id: number): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/watchlist/${id}`, { method: "DELETE" });
}

export function getWatchlistAlerts(): Promise<{
  symbol: string;
  trigger_level: number;
  planned_sl_pct: number | null;
  notes: string | null;
}[]> {
  return apiFetch("/watchlist/alerts");
}

// --- Trades ---

export function getTrades(status?: string): Promise<Trade[]> {
  const params = status ? `?status=${status}` : "";
  return apiFetch<Trade[]>(`/trades${params}`);
}

export function getTrade(id: number): Promise<Trade> {
  return apiFetch<Trade>(`/trades/${id}`);
}

export function createTrade(data: TradeCreateRequest): Promise<Trade> {
  return apiFetch<Trade>("/trades", { method: "POST", body: data });
}

export function recordPartialExit(
  tradeId: number,
  data: {
    exit_date: string;
    exit_price: number;
    exit_qty: number;
    exit_reason: string;
    notes?: string;
  },
): Promise<{ message: string; remaining_qty: number }> {
  return apiFetch(`/trades/${tradeId}/partial-exit`, { method: "PATCH", body: data });
}

export function closeTrade(
  tradeId: number,
  data: {
    exit_price: number;
    exit_reason: string;
    exit_date: string;
    exit_notes?: string;
  },
): Promise<{ message: string; gross_pnl: number }> {
  return apiFetch(`/trades/${tradeId}/close`, { method: "PATCH", body: data });
}

export function getTradeStats(): Promise<TradeStats> {
  return apiFetch<TradeStats>("/trades/stats");
}

// --- Market Stance ---

export function getLatestStance(): Promise<MarketStance | null> {
  return apiFetch<MarketStance | null>("/market-stance/latest");
}

export function logMarketStance(data: {
  log_date: string;
  strong_sectors: string[];
  weak_sectors: string[];
  stance: string;
  rpt_pct?: number;
  max_positions?: number;
  notes?: string;
}): Promise<MarketStance> {
  return apiFetch<MarketStance>("/market-stance/log", { method: "POST", body: data });
}

export function getStanceHistory(days: number = 30): Promise<MarketStance[]> {
  return apiFetch<MarketStance[]>(`/market-stance/history?days=${days}`);
}

// --- Journal ---

export function getJournals(): Promise<Journal[]> {
  return apiFetch<Journal[]>("/journal");
}

export function createJournal(data: JournalCreateRequest): Promise<Journal> {
  return apiFetch<Journal>("/journal", { method: "POST", body: data });
}

export function updateJournal(weekStart: string, data: Partial<JournalCreateRequest>): Promise<Journal> {
  return apiFetch<Journal>(`/journal/${weekStart}`, { method: "PATCH", body: data });
}

// --- Alerts (In-App) ---

export function getAlerts(unreadOnly: boolean = false): Promise<AppAlert[]> {
  const params = unreadOnly ? "?unread_only=true" : "";
  return apiFetch<AppAlert[]>(`/alerts${params}`);
}

export function markAlertRead(id: number): Promise<{ message: string }> {
  return apiFetch(`/alerts/${id}/read`, { method: "PATCH" });
}

export function markAllAlertsRead(): Promise<{ message: string }> {
  return apiFetch("/alerts/read-all", { method: "PATCH" });
}

export function getUnreadAlertCount(): Promise<{ count: number }> {
  return apiFetch("/alerts/unread-count");
}

// --- Action Alerts ---

export function checkPrices(accountValue?: number, rptPct?: number): Promise<PriceCheckResponse> {
  const params = new URLSearchParams();
  if (accountValue) params.set("account_value", String(accountValue));
  if (rptPct) params.set("rpt_pct", String(rptPct));
  const query = params.toString();
  return apiFetch<PriceCheckResponse>(`/actions/check-prices${query ? `?${query}` : ""}`, { method: "POST" });
}

export function getActionAlerts(category?: string, status?: string): Promise<ActionAlert[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (status) params.set("status", status);
  const query = params.toString();
  return apiFetch<ActionAlert[]>(`/actions${query ? `?${query}` : ""}`);
}

export function actOnAlert(id: number, actualPrice?: number, notes?: string): Promise<ActionAlert> {
  const body: Record<string, unknown> = {};
  if (actualPrice !== undefined) body.actual_price = actualPrice;
  if (notes) body.notes = notes;
  return apiFetch<ActionAlert>(`/actions/${id}/act`, {
    method: "PATCH",
    body: Object.keys(body).length > 0 ? body : undefined,
  });
}

export function dismissAlert(id: number): Promise<ActionAlert> {
  return apiFetch<ActionAlert>(`/actions/${id}/dismiss`, { method: "PATCH" });
}

// --- Simulation ---

export function runBacktest(data: {
  start_date: string;
  end_date: string;
  starting_capital: number;
  rpt_pct: number;
  name?: string;
}): Promise<SimulationRun> {
  return apiFetch<SimulationRun>("/simulation/backtest", { method: "POST", body: data });
}

export function getBacktestResult(runId: number): Promise<SimulationRunWithTrades> {
  return apiFetch<SimulationRunWithTrades>(`/simulation/backtest/${runId}`);
}

export function getBacktestProgress(runId: number): Promise<BacktestProgress> {
  return apiFetch<BacktestProgress>(`/simulation/backtest/${runId}/progress`);
}

export function cleanupStuckBacktests(): Promise<{ cleaned: number; run_ids: number[]; message: string }> {
  return apiFetch(`/simulation/cleanup-stuck`, { method: "POST" });
}

export function startPaperTrading(data: {
  starting_capital: number;
  rpt_pct: number;
  name?: string;
}): Promise<SimulationRun> {
  return apiFetch<SimulationRun>("/simulation/paper/start", { method: "POST", body: data });
}

export function processPaperDay(runId: number): Promise<{
  date: string;
  equity: number;
  cash: number;
  entries: string[];
  exits: string[];
  open_positions: number;
  prices_fetched: number;
}> {
  return apiFetch(`/simulation/paper/${runId}/process`, { method: "POST" });
}

export function getPaperStatus(runId: number): Promise<SimulationRunWithTrades> {
  return apiFetch<SimulationRunWithTrades>(`/simulation/paper/${runId}`);
}

export function stopPaperTrading(runId: number): Promise<SimulationRun> {
  return apiFetch<SimulationRun>(`/simulation/paper/${runId}/stop`, { method: "POST" });
}

export function getSimulationRuns(runType?: string): Promise<SimulationRun[]> {
  const params = runType ? `?run_type=${runType}` : "";
  return apiFetch<SimulationRun[]>(`/simulation/runs${params}`);
}

// --- Health ---

export function healthCheck(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/health");
}

// --- Admin ---

export function resetLegacyData(): Promise<{
  status: string;
  trades_archived: number;
  watchlist_cleared: number;
  scans_cleared: number;
  message: string;
}> {
  return apiFetch("/admin/reset-legacy-data", { method: "POST" });
}

// --- RS EMA50×200 Strategy ---

export function getRsStrategyStatus(): Promise<RsStrategyStatusResponse> {
  return apiFetch<RsStrategyStatusResponse>("/rs-strategy/status");
}

export function getRsStrategyTrades(): Promise<RsStrategyTradesResponse> {
  return apiFetch<RsStrategyTradesResponse>("/rs-strategy/trades");
}

export function runRsStrategyNow(): Promise<RsRunNowResult> {
  return apiFetch<RsRunNowResult>("/rs-strategy/run-now", { method: "POST" });
}
