// ---------------------------------------------------------------------------
// Intelligence API Type Definitions
// ---------------------------------------------------------------------------

// --- Regime ---

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

// --- AutoOptimize ---

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

// --- Daily Brief ---

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

// --- Risk Status ---

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

// --- Shadow Portfolio ---

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

// --- Attribution ---

export interface AttributionRow {
  signal_type: string;
  regime: string;
  trade_count: number;
  win_count: number;
  win_rate: number;
  avg_r: number;
  total_r: number;
}

// --- Learning Progress ---

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

// --- Backend raw response shapes (what the Python API actually returns) ---

export interface RawRegimeResponse {
  regime: {
    regime: string;
    date: string | null;
    nifty_adx: number;
    india_vix: number;
    hurst_exponent: number;
    param_bank_version: string | null;
  } | null;
  parameter_banks: Record<string, Record<string, number>> | null;
}

export interface RawBriefResponse {
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

export interface RawRiskResponse {
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

export interface RawOptimizeStatus {
  running: boolean;
  enabled?: boolean;
  last_result?: { timestamp?: string; new_score?: number } | null;
  current_parameters?: Record<string, number>;
  [key: string]: unknown;
}

export interface RawOptimizeHistory {
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

export interface RawStrategyResponse {
  parameters: Record<string, number>;
  bounds: Record<string, [number, number]>;
  valid: boolean;
  violations: string[];
}

export interface RawShadowResponse {
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

export interface RawAttributionResponse {
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

// --- Internal fetch helper ---

export interface IntelligenceRequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}
