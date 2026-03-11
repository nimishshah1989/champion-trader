const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Shared fetch helper (mirrors api.ts pattern)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Types — Regime
// ---------------------------------------------------------------------------

export type RegimeType =
  | "TRENDING_BULL"
  | "RANGING_QUIET"
  | "HIGH_VOLATILITY"
  | "WEAKENING_BEAR";

export interface RegimeData {
  regime: RegimeType;
  adx: number;
  vix: number;
  hurst: number;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Types — AutoOptimize
// ---------------------------------------------------------------------------

export interface OptimizeStatus {
  running: boolean;
  last_run: string | null;
  current_best_score: number | null;
  total_experiments: number;
  keep_count: number;
  revert_count: number;
}

export interface ExperimentRecord {
  id: number;
  timestamp: string;
  parameter: string;
  old_value: number;
  new_value: number;
  hypothesis: string;
  old_score: number;
  new_score: number;
  outcome: "KEEP" | "REVERT";
}

export interface OptimizeHistory {
  experiments: ExperimentRecord[];
  total_experiments: number;
  keep_rate: number;
  best_score: number;
  most_improved_parameter: string | null;
}

export interface StrategyParameter {
  name: string;
  value: number;
  min_bound: number;
  max_bound: number;
  description: string;
}

// ---------------------------------------------------------------------------
// Types — Daily Brief
// ---------------------------------------------------------------------------

export interface DailyBrief {
  date: string;
  brief_text: string;
  generated_at: string;
  regime: RegimeType;
  top_setups: SetupCard[];
}

export interface SetupCard {
  symbol: string;
  signal_type: string;
  score: number;
  entry_price: number;
  stop_loss: number;
  target: number;
  rationale: string;
}

// ---------------------------------------------------------------------------
// Types — Risk Status
// ---------------------------------------------------------------------------

export interface RiskStatus {
  open_positions: number;
  total_risk_pct: number;
  max_risk_pct: number;
  frozen: boolean;
  frozen_reason: string | null;
  positions: RiskPosition[];
}

export interface RiskPosition {
  symbol: string;
  risk_pct: number;
  entry_price: number;
  sl_price: number;
  qty: number;
}

// ---------------------------------------------------------------------------
// Types — Shadow Portfolio
// ---------------------------------------------------------------------------

export interface ShadowComparison {
  shadow_win_rate: number;
  live_win_rate: number;
  shadow_avg_r: number;
  live_avg_r: number;
  human_alpha: number;
  verdict: string;
  approved_win_rate: number;
  skipped_win_rate: number;
  trades: ShadowTrade[];
}

export interface ShadowTrade {
  id: number;
  signal_date: string;
  symbol: string;
  signal_type: string;
  score: number;
  entry: number;
  stop: number;
  target: number;
  was_approved: boolean;
  paper_exit: number | null;
  paper_r: number | null;
  paper_pnl: number | null;
}

// ---------------------------------------------------------------------------
// Types — Attribution
// ---------------------------------------------------------------------------

export interface AttributionRow {
  signal_type: string;
  regime: string;
  trade_count: number;
  win_count: number;
  win_rate: number;
  avg_r: number;
  total_r: number;
}

// ---------------------------------------------------------------------------
// API Functions — Regime
// ---------------------------------------------------------------------------

export function getRegime(): Promise<RegimeData> {
  return apiFetch<RegimeData>("/api/intelligence/regime");
}

// ---------------------------------------------------------------------------
// API Functions — AutoOptimize
// ---------------------------------------------------------------------------

export function getOptimizeStatus(): Promise<OptimizeStatus> {
  return apiFetch<OptimizeStatus>("/api/intelligence/optimize/status");
}

export function getOptimizeHistory(): Promise<OptimizeHistory> {
  return apiFetch<OptimizeHistory>("/api/intelligence/optimize/history");
}

export function startOptimize(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/intelligence/optimize/start", { method: "POST" });
}

export function stopOptimize(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/intelligence/optimize/stop", { method: "POST" });
}

export function getStrategyParameters(): Promise<StrategyParameter[]> {
  return apiFetch<StrategyParameter[]>("/api/intelligence/strategy/parameters");
}

// ---------------------------------------------------------------------------
// API Functions — Daily Brief
// ---------------------------------------------------------------------------

export function getDailyBrief(): Promise<DailyBrief> {
  return apiFetch<DailyBrief>("/api/intelligence/brief");
}

// ---------------------------------------------------------------------------
// API Functions — Risk
// ---------------------------------------------------------------------------

export function getRiskStatus(): Promise<RiskStatus> {
  return apiFetch<RiskStatus>("/api/intelligence/risk/status");
}

// ---------------------------------------------------------------------------
// API Functions — Shadow Portfolio
// ---------------------------------------------------------------------------

export function getShadowComparison(): Promise<ShadowComparison> {
  return apiFetch<ShadowComparison>("/api/intelligence/shadow");
}

// ---------------------------------------------------------------------------
// API Functions — Attribution
// ---------------------------------------------------------------------------

export function getAttribution(): Promise<AttributionRow[]> {
  return apiFetch<AttributionRow[]>("/api/intelligence/attribution");
}
