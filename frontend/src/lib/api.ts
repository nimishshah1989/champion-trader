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

// --- Health ---

export function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/health");
}
