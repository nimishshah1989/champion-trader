const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

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

export interface ScanResult {
  id: number;
  scan_date: string;
  symbol: string;
  scan_type: string;
  close_price: number | null;
  volume: number | null;
  avg_volume_20d: number | null;
  volume_ratio: number | null;
  trp: number | null;
  avg_trp: number | null;
  trp_ratio: number | null;
  candle_body_pct: number | null;
  close_position: number | null;
  stage: string | null;
  above_30w_ma: boolean | null;
  ma_trending_up: boolean | null;
  base_days: number | null;
  has_min_20_bar_base: boolean | null;
  base_quality: string | null;
  adt: number | null;
  passes_liquidity_filter: boolean | null;
  wuc_type: string | null;
  watchlist_bucket: string | null;
  trigger_level: number | null;
  notes: string | null;
}

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

export interface PositionCalcRequest {
  symbol: string;
  account_value: number;
  rpt_pct: number;
  entry_price: number;
  trp_pct: number;
}

export interface PositionCalcResponse {
  rpt_amount: number;
  sl_price: number;
  sl_pct: number;
  sl_amount: number;
  position_value: number;
  position_size: number;
  half_qty: number;
  target_2r: number;
  target_ne: number;
  target_ge: number;
  target_ee: number;
}

export function calculatePosition(data: PositionCalcRequest): Promise<PositionCalcResponse> {
  return apiFetch<PositionCalcResponse>("/calculator/position", {
    method: "POST",
    body: data,
  });
}

// --- Watchlist ---

export interface WatchlistItem {
  id: number;
  symbol: string;
  added_date: string;
  bucket: string;
  stage: string | null;
  base_days: number | null;
  base_quality: string | null;
  wuc_types: string | null;
  trigger_level: number | null;
  planned_entry_price: number | null;
  planned_sl_pct: number | null;
  planned_position_size: number | null;
  planned_half_qty: number | null;
  status: string;
  notes: string | null;
}

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

export interface Trade {
  id: number;
  symbol: string;
  entry_date: string;
  entry_type: string | null;
  avg_entry_price: number | null;
  total_qty: number | null;
  sl_price: number | null;
  sl_pct: number | null;
  rpt_amount: number | null;
  target_2r: number | null;
  target_ne: number | null;
  target_ge: number | null;
  target_ee: number | null;
  status: string;
  remaining_qty: number | null;
  gross_pnl: number | null;
  r_multiple: number | null;
  pnl_pct: number | null;
  setup_type: string | null;
}

export interface TradeStats {
  total_trades: number;
  open_trades: number;
  closed_trades: number;
  win_count: number;
  loss_count: number;
  win_rate: number | null;
  avg_r_multiple: number | null;
  arr: number | null;
  total_pnl: number;
}

export function getTrades(status?: string): Promise<Trade[]> {
  const params = status ? `?status=${status}` : "";
  return apiFetch<Trade[]>(`/trades${params}`);
}

export function getTrade(id: number): Promise<Trade> {
  return apiFetch<Trade>(`/trades/${id}`);
}

export interface TradeCreateRequest {
  symbol: string;
  entry_date: string;
  entry_type?: string;
  entry_price_half1: number;
  entry_price_half2?: number;
  qty_half1: number;
  qty_half2?: number;
  total_qty: number;
  avg_entry_price: number;
  trp_at_entry: number;
  sl_price: number;
  sl_pct: number;
  rpt_amount: number;
  target_2r?: number;
  target_ne?: number;
  target_ge?: number;
  target_ee?: number;
  market_stance_at_entry?: string;
  setup_type?: string;
  entry_notes?: string;
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

export interface MarketStance {
  id: number;
  log_date: string;
  strong_sectors: string | null;
  weak_sectors: string | null;
  strong_count: number | null;
  weak_count: number | null;
  stance: string | null;
  rpt_pct: number | null;
  max_positions: number | null;
  notes: string | null;
}

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

export interface Journal {
  id: number;
  week_start: string;
  week_end: string;
  account_value_start: number | null;
  account_value_end: number | null;
  weekly_return_pct: number | null;
  trades_taken: number | null;
  win_count: number | null;
  loss_count: number | null;
  win_rate: number | null;
  arr: number | null;
  excelled_at: string | null;
  poor_at: string | null;
  key_learnings: string | null;
}

export function getJournals(): Promise<Journal[]> {
  return apiFetch<Journal[]>("/journal");
}

export interface JournalCreateRequest {
  week_start: string;
  week_end: string;
  account_value_start?: number;
  account_value_end?: number;
  grave_casual_trade?: boolean;
  grave_sl_violation?: boolean;
  grave_risk_exceeded?: boolean;
  grave_averaged_down?: boolean;
  grave_rebought_loser?: boolean;
  rm_winrate_arr_eval?: string;
  rm_market_stance_accuracy?: string;
  rm_rpt_consistency?: string;
  rm_or_matrix_violated?: boolean;
  rm_slippage_issues?: string;
  rm_streak_handling?: string;
  tech_random_trades?: string;
  tech_poor_setups?: string;
  tech_entry_timing?: string;
  tech_sl_placement?: string;
  tech_exit_framework?: string;
  tech_extension_judgment?: string;
  tech_earnings_handling?: string;
  routine_scans_daily?: boolean;
  routine_watchlist_updated?: boolean;
  routine_setup_tracker_updated?: boolean;
  routine_screen_time_minimised?: boolean;
  routine_historical_analysis?: string;
  psych_affirmations_read?: boolean;
  psych_impulsive_actions?: string;
  psych_fear_greed_influence?: string;
  psych_social_trading_influence?: boolean;
  psych_stress_level?: string;
  excelled_at?: string;
  poor_at?: string;
  key_learnings?: string;
}

export function createJournal(data: JournalCreateRequest): Promise<Journal> {
  return apiFetch<Journal>("/journal", { method: "POST", body: data });
}

export function updateJournal(weekStart: string, data: Partial<JournalCreateRequest>): Promise<Journal> {
  return apiFetch<Journal>(`/journal/${weekStart}`, { method: "PATCH", body: data });
}

// --- Alerts (In-App) ---

export interface AppAlert {
  id: number;
  alert_type: string;
  symbol: string | null;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  created_at: string;
  data: string | null;
}

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

export interface ActionAlert {
  id: number;
  alert_category: string;
  alert_type: string;
  symbol: string;
  current_price: number | null;
  trigger_price: number | null;
  suggested_qty: number | null;
  suggested_half_qty: number | null;
  suggested_sl_price: number | null;
  suggested_entry_price: number | null;
  account_value_used: number | null;
  rpt_pct_used: number | null;
  trp_pct: number | null;
  trade_id: number | null;
  exit_qty: number | null;
  exit_pct: number | null;
  target_level: number | null;
  remaining_qty_after: number | null;
  action_text: string | null;
  status: string;
  acted_at: string | null;
  resulting_trade_id: number | null;
  resulting_partial_exit_id: number | null;
  source: string | null;
  watchlist_id: number | null;
  data: string | null;
  created_at: string | null;
}

export interface PriceCheckResponse {
  buy_alerts: ActionAlert[];
  sell_alerts: ActionAlert[];
  last_checked: string;
  prices_fetched: number;
}

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

export interface SimulationRun {
  id: number;
  run_type: string;
  name: string | null;
  starting_capital: number;
  rpt_pct: number;
  start_date: string | null;
  end_date: string | null;
  status: string;
  final_capital: number | null;
  total_pnl: number | null;
  total_return_pct: number | null;
  total_trades: number;
  win_count: number;
  loss_count: number;
  win_rate: number | null;
  avg_win_r: number | null;
  avg_loss_r: number | null;
  arr: number | null;
  expectancy: number | null;
  max_drawdown_pct: number | null;
  max_drawdown_amount: number | null;
  equity_curve: string | null;
  last_processed_date: string | null;
  error_message: string | null;
  created_at: string | null;
}

export interface SimulationTrade {
  id: number;
  run_id: number;
  symbol: string;
  signal_date: string | null;
  entry_date: string | null;
  entry_price: number | null;
  total_qty: number | null;
  half_qty: number | null;
  trp_pct: number | null;
  sl_price: number | null;
  rpt_amount: number | null;
  target_2r: number | null;
  target_ne: number | null;
  target_ge: number | null;
  target_ee: number | null;
  qty_exited_2r: number;
  qty_exited_ne: number;
  qty_exited_ge: number;
  qty_exited_ee: number;
  qty_exited_sl: number;
  qty_exited_final: number;
  remaining_qty: number | null;
  status: string;
  exit_date: string | null;
  gross_pnl: number | null;
  r_multiple: number | null;
  pnl_pct: number | null;
  portfolio_value_at_entry: number | null;
}

export interface SimulationRunWithTrades extends SimulationRun {
  trades: SimulationTrade[];
}

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

export interface BacktestProgress {
  run_id: number;
  status: string;
  phase: string;
  progress_pct: number;
  days_total?: number;
  days_done?: number;
  current_date?: string;
  open_positions?: number;
  stocks?: number;
  error_message?: string | null;
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

export interface ScheduledJob {
  id: string;
  name: string;
  next_run: string;
}

export interface HealthStatus {
  status: string;
  scheduler: "running" | "stopped";
  scheduled_jobs: number;
  jobs: ScheduledJob[];
}

export function healthCheck(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/health");
}
