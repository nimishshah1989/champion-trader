// ---------------------------------------------------------------------------
// Intelligence API client — transforms backend responses to frontend types
//
// The backend returns raw dict shapes (Python-style). This module normalizes
// them into the typed interfaces the React components consume.
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const MAX_RISK_PCT_DEFAULT = 10;
const WIN_RATE_SCALE = 100;

// ---------------------------------------------------------------------------
// Shared fetch helper
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
// Helpers
// ---------------------------------------------------------------------------

/** Parse a value to number, returning fallback if NaN */
function num(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isNaN(n) ? fallback : n;
}

/** Scale a 0-1 ratio to 0-100 percentage if it looks like a ratio */
function pct(v: unknown): number {
  const n = num(v, 0);
  // Backend returns win_rate as 0-1 ratio; if value is <= 1 and not 0, scale up
  return n > 0 && n <= 1 ? n * WIN_RATE_SCALE : n;
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
// Backend raw response shapes (what the Python API actually returns)
// ---------------------------------------------------------------------------

/* eslint-disable @typescript-eslint/no-explicit-any */
interface RawRegimeResponse {
  regime: {
    regime: string;
    date: string | null;
    nifty_adx: number;
    india_vix: number;
    hurst_exponent: number;
    param_bank_version: string | null;
  } | null;
  parameter_banks: any;
}

interface RawBriefResponse {
  date?: string;
  brief_text?: string;
  generated_at?: string;
  regime?: { regime: string } | string;
  setups?: Array<{
    symbol: string;
    composite_score: number;
    scan_type: string;
    entry_price: number;
    stop_price: number;
    target_2r: number;
    rr_ratio?: number;
    risk_amount?: number;
    base_days?: number;
    base_quality?: string;
  }>;
  top_setups?: SetupCard[];
  recommendation?: string;
  error?: string;
}

interface RawRiskResponse {
  frozen: boolean;
  open_positions: number;
  risk: {
    total_risk_amount: number;
    total_risk_pct: number;
    exceeds_limit: boolean;
    per_position: Array<{
      symbol: string;
      risk_amount: number;
      risk_pct: number;
    }>;
  };
}

interface RawOptimizeStatus {
  running: boolean;
  enabled?: boolean;
  last_result?: { timestamp?: string; new_score?: number } | null;
  current_parameters?: Record<string, number>;
  [key: string]: any;
}

interface RawOptimizeHistory {
  experiments: Array<{
    timestamp: string;
    parameter: string;
    old_value: string | number;
    new_value: string | number;
    hypothesis: string;
    old_score: string | number;
    new_score: string | number;
    outcome: string;
    trade_count?: string | number;
    expectancy?: string | number;
    max_dd?: string | number;
  }>;
  summary: {
    total_experiments: number;
    keep_count: number;
    revert_count: number;
    error_count?: number;
    keep_rate_pct: number;
    most_improved_parameter: string | null;
    best_score: number | null;
    latest_score?: number | null;
  };
}

interface RawStrategyResponse {
  parameters: Record<string, number>;
  bounds: Record<string, [number, number]>;
  valid: boolean;
  violations: string[];
}

interface RawShadowResponse {
  shadow_trades?: number;
  shadow_win_rate?: number;
  shadow_avg_r?: number;
  shadow_total_r?: number;
  approved_count?: number;
  approved_win_rate?: number;
  skipped_count?: number;
  skipped_win_rate?: number;
  live_trades?: number;
  live_win_rate?: number;
  live_avg_r?: number;
  live_total_r?: number;
  human_alpha?: number;
  verdict?: string;
  sufficient_data?: boolean;
  message?: string;
  trades?: ShadowTrade[];
}

interface RawAttributionResponse {
  attribution: Array<{
    signal_type: string;
    regime: string;
    trade_count: number;
    win_count: number;
    win_rate: number;
    avg_r: number;
    total_r: number;
  }>;
}
/* eslint-enable @typescript-eslint/no-explicit-any */

// ---------------------------------------------------------------------------
// Parameter descriptions (static — backend doesn't include these)
// ---------------------------------------------------------------------------

const PARAM_DESCRIPTIONS: Record<string, string> = {
  ppc_trp_ratio_min: "Minimum TRP ratio for PPC signals",
  ppc_close_position_min: "Min close-in-range for PPC candles",
  ppc_volume_ratio_min: "Min volume ratio for PPC signals",
  npc_trp_ratio_min: "Minimum TRP ratio for NPC signals",
  npc_close_position_max: "Max close-in-range for NPC candles",
  npc_volume_ratio_min: "Min volume ratio for NPC signals",
  contraction_atr_lookback: "ATR lookback period for contraction",
  contraction_narrowing_min: "Min narrowing bars for contraction",
  contraction_resistance_pct: "Resistance proximity % for contraction",
  min_base_days: "Minimum days in base formation",
  sma_window: "SMA window for stage analysis",
  stage_sma_lookback: "Lookback period for SMA slope",
  min_adt_crore: "Min average daily turnover (₹ Cr)",
  weight_ppc: "Composite score weight: PPC",
  weight_contraction: "Composite score weight: Contraction",
  weight_npc_filter: "Composite score weight: NPC filter",
};

// ---------------------------------------------------------------------------
// API Functions — Regime
// ---------------------------------------------------------------------------

export async function getRegime(): Promise<RegimeData> {
  const raw = await apiFetch<RawRegimeResponse>("/api/intelligence/regime");

  const r = raw.regime;
  if (!r || typeof r !== "object") {
    throw new Error("No regime data available");
  }

  return {
    regime: (r.regime ?? "UNKNOWN") as RegimeType,
    adx: num(r.nifty_adx),
    vix: num(r.india_vix),
    hurst: num(r.hurst_exponent),
    timestamp: r.date ?? "",
  };
}

// ---------------------------------------------------------------------------
// API Functions — AutoOptimize
// ---------------------------------------------------------------------------

export async function getOptimizeStatus(): Promise<OptimizeStatus> {
  const raw = await apiFetch<RawOptimizeStatus>("/api/intelligence/optimize/status");

  return {
    running: raw.running ?? false,
    last_run: raw.last_result?.timestamp ?? null,
    current_best_score: raw.last_result?.new_score ?? null,
    total_experiments: 0,
    keep_count: 0,
    revert_count: 0,
  };
}

export async function getOptimizeHistory(): Promise<OptimizeHistory> {
  const raw = await apiFetch<RawOptimizeHistory>("/api/intelligence/optimize/history");

  const experiments: ExperimentRecord[] = Array.isArray(raw.experiments)
    ? raw.experiments.map((exp, idx) => ({
        id: idx + 1,
        timestamp: String(exp.timestamp ?? ""),
        parameter: String(exp.parameter ?? ""),
        old_value: num(exp.old_value),
        new_value: num(exp.new_value),
        hypothesis: String(exp.hypothesis ?? ""),
        old_score: num(exp.old_score),
        new_score: num(exp.new_score),
        outcome: (String(exp.outcome ?? "REVERT").toUpperCase() === "KEEP" ? "KEEP" : "REVERT") as "KEEP" | "REVERT",
      }))
    : [];

  const summary = raw.summary ?? { total_experiments: 0, keep_count: 0, revert_count: 0, keep_rate_pct: 0, most_improved_parameter: null, best_score: null };

  return {
    experiments,
    total_experiments: num(summary.total_experiments),
    keep_rate: num(summary.keep_rate_pct),
    best_score: num(summary.best_score),
    most_improved_parameter: summary.most_improved_parameter ?? null,
  };
}

export function startOptimize(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/intelligence/optimize/start", { method: "POST" });
}

export function stopOptimize(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/intelligence/optimize/stop", { method: "POST" });
}

export async function getStrategyParameters(): Promise<StrategyParameter[]> {
  const raw = await apiFetch<RawStrategyResponse>("/api/intelligence/strategy/parameters");

  const params = raw.parameters ?? {};
  const bounds = raw.bounds ?? {};

  return Object.entries(params).map(([name, value]) => {
    const [minBound, maxBound] = bounds[name] ?? [0, 100];
    return {
      name,
      value: num(value),
      min_bound: num(minBound),
      max_bound: num(maxBound),
      description: PARAM_DESCRIPTIONS[name] ?? name.replace(/_/g, " "),
    };
  });
}

// ---------------------------------------------------------------------------
// API Functions — Daily Brief
// ---------------------------------------------------------------------------

export async function getDailyBrief(): Promise<DailyBrief> {
  const raw = await apiFetch<RawBriefResponse>("/api/intelligence/brief");

  if (raw.error) {
    throw new Error(raw.error);
  }

  // Regime can be an object {regime: "TRENDING_BULL", ...} or a string
  let regimeStr: RegimeType = "TRENDING_BULL";
  if (typeof raw.regime === "string") {
    regimeStr = raw.regime as RegimeType;
  } else if (raw.regime && typeof raw.regime === "object" && "regime" in raw.regime) {
    regimeStr = raw.regime.regime as RegimeType;
  }

  // Map backend "setups" (with different field names) to frontend SetupCard[]
  // Backend uses: {composite_score, scan_type, stop_price, target_2r, base_quality, ...}
  // Frontend uses: {score, signal_type, stop_loss, target, rationale, ...}
  const rawSetups: unknown[] = Array.isArray(raw.setups)
    ? raw.setups
    : Array.isArray(raw.top_setups)
      ? raw.top_setups
      : [];

  function mapSetup(s: Record<string, unknown>): SetupCard {
    return {
      symbol: String(s.symbol ?? ""),
      signal_type: String(s.scan_type ?? s.signal_type ?? ""),
      score: num(s.composite_score ?? s.score),
      entry_price: num(s.entry_price),
      stop_loss: num(s.stop_price ?? s.stop_loss),
      target: num(s.target_2r ?? s.target),
      rationale: String(
        s.base_quality
          ? `${s.base_quality} base, ${s.base_days ?? 0} days, RR ${num(s.rr_ratio).toFixed(1)}`
          : s.rationale ?? ""
      ),
    };
  }

  const topSetups: SetupCard[] = rawSetups.map((s) => mapSetup(s as Record<string, unknown>));

  return {
    date: String(raw.date ?? ""),
    brief_text: typeof raw.brief_text === "string" ? raw.brief_text : "",
    generated_at: String(raw.generated_at ?? ""),
    regime: regimeStr,
    top_setups: topSetups,
  };
}

// ---------------------------------------------------------------------------
// API Functions — Risk
// ---------------------------------------------------------------------------

export async function getRiskStatus(): Promise<RiskStatus> {
  const raw = await apiFetch<RawRiskResponse>("/api/intelligence/risk/status");

  const risk = raw.risk ?? { total_risk_pct: 0, exceeds_limit: false, per_position: [] };

  return {
    open_positions: num(raw.open_positions),
    total_risk_pct: num(risk.total_risk_pct),
    max_risk_pct: MAX_RISK_PCT_DEFAULT,
    frozen: raw.frozen ?? false,
    frozen_reason: null,
    positions: Array.isArray(risk.per_position)
      ? risk.per_position.map((p) => ({
          symbol: String(p.symbol ?? ""),
          risk_pct: num(p.risk_pct),
          entry_price: 0,
          sl_price: 0,
          qty: 0,
        }))
      : [],
  };
}

// ---------------------------------------------------------------------------
// API Functions — Shadow Portfolio
// ---------------------------------------------------------------------------

export async function getShadowComparison(): Promise<ShadowComparison> {
  const raw = await apiFetch<RawShadowResponse>("/api/intelligence/shadow");

  return {
    shadow_win_rate: pct(raw.shadow_win_rate),
    live_win_rate: pct(raw.live_win_rate),
    shadow_avg_r: num(raw.shadow_avg_r),
    live_avg_r: num(raw.live_avg_r),
    human_alpha: num(raw.human_alpha),
    verdict: String(raw.verdict ?? raw.message ?? "Insufficient data"),
    approved_win_rate: pct(raw.approved_win_rate),
    skipped_win_rate: pct(raw.skipped_win_rate),
    trades: Array.isArray(raw.trades) ? raw.trades : [],
  };
}

// ---------------------------------------------------------------------------
// Types — Learning Progress
// ---------------------------------------------------------------------------

export interface LearningProgress {
  loop_status: {
    closed: boolean;
    issues: string[];
    description: string;
  };
  current_regime: {
    regime: string;
    date: string | null;
    nifty_adx: number;
    india_vix: number;
    hurst_exponent: number;
  };
  regime_banks: {
    active_regime: string | null;
    active_version: string;
    banks: Record<string, { overrides: Record<string, number>; override_count: number }>;
  };
  parameters: Record<string, {
    base_value: number;
    effective_value: number;
    regime_adjusted: boolean;
    bound_low: number;
    bound_high: number;
    position_in_range: number;
    experiments_run: number;
    improvements: number;
  }>;
  experiment_summary: {
    total_experiments: number;
    keep_count: number;
    revert_count: number;
    error_count: number;
    keep_rate_pct: number;
    most_improved_parameter: string | null;
    best_score: number | null;
    latest_score: number | null;
    first_experiment: string | null;
    latest_experiment: string | null;
  };
  experiment_timeline: Array<{
    timestamp: string;
    parameter: string;
    outcome: string;
    score_delta: number | null;
  }>;
  learning_velocity: {
    recent_keep_rate: number;
    older_keep_rate: number | null;
    trend: string;
    total_experiments: number;
  };
}

// ---------------------------------------------------------------------------
// API Functions — Learning Progress
// ---------------------------------------------------------------------------

export async function getLearningProgress(): Promise<LearningProgress> {
  return apiFetch<LearningProgress>("/api/intelligence/learning-progress");
}

// ---------------------------------------------------------------------------
// API Functions — Attribution
// ---------------------------------------------------------------------------

export async function getAttribution(): Promise<AttributionRow[]> {
  const raw = await apiFetch<RawAttributionResponse | AttributionRow[]>("/api/intelligence/attribution");

  // Backend wraps in {attribution: [...]}, handle both wrapped and bare array
  const rows: AttributionRow[] = Array.isArray(raw)
    ? raw
    : Array.isArray((raw as RawAttributionResponse).attribution)
      ? (raw as RawAttributionResponse).attribution
      : [];

  // Scale win_rate from 0-1 → 0-100 if needed
  return rows.map((r) => ({
    signal_type: String(r.signal_type ?? ""),
    regime: String(r.regime ?? ""),
    trade_count: num(r.trade_count),
    win_count: num(r.win_count),
    win_rate: pct(r.win_rate),
    avg_r: num(r.avg_r),
    total_r: num(r.total_r),
  }));
}
