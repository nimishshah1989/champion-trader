import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { Mock } from "vitest";

const mockFetch = vi.fn() as Mock;
vi.stubGlobal("fetch", mockFetch);

const {
  getRegime,
  getOptimizeStatus,
  getOptimizeHistory,
  startOptimize,
  stopOptimize,
  getStrategyParameters,
  getDailyBrief,
  getRiskStatus,
  getShadowComparison,
  getAttribution,
  getLearningProgress,
} = await import("../intelligence-api");

function okResponse(data: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers(),
    redirected: false,
    statusText: "OK",
    type: "basic",
    url: "",
    clone: () => ({} as Response),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

function errResponse(status: number, body: string): Response {
  return {
    ok: false,
    status,
    json: () => Promise.reject(new Error("not json")),
    text: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    statusText: "Error",
    type: "basic",
    url: "",
    clone: () => ({} as Response),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getRegime", () => {
  it("transforms raw regime response to RegimeData", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      regime: {
        regime: "TRENDING_BULL",
        date: "2025-03-15",
        nifty_adx: 28.5,
        india_vix: 14.2,
        hurst_exponent: 0.65,
        param_bank_version: "v1",
      },
      parameter_banks: null,
    }));

    const result = await getRegime();

    expect(result).toEqual({
      regime: "TRENDING_BULL",
      adx: 28.5,
      vix: 14.2,
      hurst: 0.65,
      timestamp: "2025-03-15",
    });
  });

  it("throws when regime data is null", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ regime: null, parameter_banks: null }));

    await expect(getRegime()).rejects.toThrow("No regime data available");
  });

  it("defaults missing fields to 0 or empty string", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      regime: {
        regime: null,
        date: null,
        nifty_adx: null,
        india_vix: null,
        hurst_exponent: null,
        param_bank_version: null,
      },
      parameter_banks: null,
    }));

    const result = await getRegime();

    expect(result.regime).toBe("UNKNOWN");
    expect(result.adx).toBe(0);
    expect(result.vix).toBe(0);
    expect(result.hurst).toBe(0);
    expect(result.timestamp).toBe("");
  });
});

describe("getOptimizeStatus", () => {
  it("transforms raw status response", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      running: true,
      enabled: true,
      last_result: { timestamp: "2025-03-15T10:00:00", new_score: 85.5 },
      current_parameters: {},
    }));

    const result = await getOptimizeStatus();

    expect(result).toEqual({
      running: true,
      last_run: "2025-03-15T10:00:00",
      current_best_score: 85.5,
      total_experiments: 0,
      keep_count: 0,
      revert_count: 0,
    });
  });

  it("handles missing last_result", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      running: false,
      last_result: null,
    }));

    const result = await getOptimizeStatus();

    expect(result.last_run).toBeNull();
    expect(result.current_best_score).toBeNull();
  });
});

describe("getOptimizeHistory", () => {
  it("transforms experiments and summary", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      experiments: [
        {
          timestamp: "2025-03-15T10:00:00",
          parameter: "ppc_trp_ratio_min",
          old_value: "1.5",
          new_value: "1.8",
          hypothesis: "Increase TRP threshold",
          old_score: "70",
          new_score: "75",
          outcome: "KEEP",
        },
      ],
      summary: {
        total_experiments: 10,
        keep_count: 6,
        revert_count: 4,
        keep_rate_pct: 60,
        most_improved_parameter: "ppc_trp_ratio_min",
        best_score: 85,
      },
    }));

    const result = await getOptimizeHistory();

    expect(result.experiments).toHaveLength(1);
    expect(result.experiments[0]).toEqual({
      id: 1,
      timestamp: "2025-03-15T10:00:00",
      parameter: "ppc_trp_ratio_min",
      old_value: 1.5,
      new_value: 1.8,
      hypothesis: "Increase TRP threshold",
      old_score: 70,
      new_score: 75,
      outcome: "KEEP",
    });
    expect(result.total_experiments).toBe(10);
    expect(result.keep_rate).toBe(60);
    expect(result.best_score).toBe(85);
    expect(result.most_improved_parameter).toBe("ppc_trp_ratio_min");
  });

  it("handles empty experiments array", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      experiments: [],
      summary: {
        total_experiments: 0,
        keep_count: 0,
        revert_count: 0,
        keep_rate_pct: 0,
        most_improved_parameter: null,
        best_score: null,
      },
    }));

    const result = await getOptimizeHistory();

    expect(result.experiments).toEqual([]);
    expect(result.total_experiments).toBe(0);
  });

  it("normalizes REVERT outcomes for unknown strings", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      experiments: [
        {
          timestamp: "2025-03-15",
          parameter: "test",
          old_value: 1,
          new_value: 2,
          hypothesis: "",
          old_score: 50,
          new_score: 45,
          outcome: "error",
        },
      ],
      summary: {
        total_experiments: 1,
        keep_count: 0,
        revert_count: 1,
        keep_rate_pct: 0,
        most_improved_parameter: null,
        best_score: null,
      },
    }));

    const result = await getOptimizeHistory();

    expect(result.experiments[0].outcome).toBe("REVERT");
  });
});

describe("startOptimize / stopOptimize", () => {
  it("startOptimize sends POST", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ message: "Started" }));

    const result = await startOptimize();

    expect(result).toEqual({ message: "Started" });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/intelligence/optimize/start"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("stopOptimize sends POST", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ message: "Stopped" }));

    const result = await stopOptimize();

    expect(result).toEqual({ message: "Stopped" });
  });
});

describe("getStrategyParameters", () => {
  it("transforms parameters with bounds and descriptions", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      parameters: {
        ppc_trp_ratio_min: 1.5,
        min_base_days: 20,
      },
      bounds: {
        ppc_trp_ratio_min: [0.5, 5.0],
        min_base_days: [10, 50],
      },
      valid: true,
      violations: [],
    }));

    const result = await getStrategyParameters();

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      name: "ppc_trp_ratio_min",
      value: 1.5,
      min_bound: 0.5,
      max_bound: 5.0,
      description: "Minimum TRP ratio for PPC signals",
    });
    expect(result[1]).toEqual({
      name: "min_base_days",
      value: 20,
      min_bound: 10,
      max_bound: 50,
      description: "Minimum days in base formation",
    });
  });

  it("handles missing bounds with defaults", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      parameters: { unknown_param: 42 },
      bounds: {},
      valid: true,
      violations: [],
    }));

    const result = await getStrategyParameters();

    expect(result[0].min_bound).toBe(0);
    expect(result[0].max_bound).toBe(100);
    // Unknown param gets name-based description
    expect(result[0].description).toBe("unknown param");
  });
});

describe("getDailyBrief", () => {
  it("transforms backend brief with setups", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      date: "2025-03-15",
      brief_text: "Market is trending bullish",
      generated_at: "2025-03-15T17:00:00",
      regime: { regime: "TRENDING_BULL" },
      setups: [
        {
          symbol: "RELIANCE",
          composite_score: 85,
          scan_type: "PPC",
          entry_price: 2500,
          stop_price: 2400,
          target_2r: 2700,
          rr_ratio: 2.0,
          base_days: 25,
          base_quality: "GOOD",
        },
      ],
    }));

    const result = await getDailyBrief();

    expect(result.date).toBe("2025-03-15");
    expect(result.regime).toBe("TRENDING_BULL");
    expect(result.top_setups).toHaveLength(1);
    expect(result.top_setups[0].symbol).toBe("RELIANCE");
    expect(result.top_setups[0].signal_type).toBe("PPC");
    expect(result.top_setups[0].score).toBe(85);
    expect(result.top_setups[0].stop_loss).toBe(2400);
    expect(result.top_setups[0].target).toBe(2700);
    expect(result.top_setups[0].rationale).toContain("GOOD base");
  });

  it("handles regime as string", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      date: "2025-03-15",
      brief_text: "",
      generated_at: "",
      regime: "HIGH_VOLATILITY",
      setups: [],
    }));

    const result = await getDailyBrief();

    expect(result.regime).toBe("HIGH_VOLATILITY");
  });

  it("throws when error field is present", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      error: "No brief available",
    }));

    await expect(getDailyBrief()).rejects.toThrow("No brief available");
  });

  it("uses top_setups when setups is missing", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      date: "2025-03-15",
      brief_text: "",
      generated_at: "",
      regime: "RANGING_QUIET",
      top_setups: [
        { symbol: "TCS", signal_type: "NPC", score: 70, entry_price: 3500, stop_loss: 3400, target: 3700, rationale: "test" },
      ],
    }));

    const result = await getDailyBrief();

    expect(result.top_setups).toHaveLength(1);
    expect(result.top_setups[0].symbol).toBe("TCS");
  });
});

describe("getRiskStatus", () => {
  it("transforms raw risk response", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      frozen: false,
      open_positions: 3,
      risk: {
        total_risk_amount: 15000,
        total_risk_pct: 3.0,
        exceeds_limit: false,
        per_position: [
          { symbol: "RELIANCE", risk_amount: 5000, risk_pct: 1.0 },
          { symbol: "TCS", risk_amount: 5000, risk_pct: 1.0 },
        ],
      },
    }));

    const result = await getRiskStatus();

    expect(result.open_positions).toBe(3);
    expect(result.total_risk_pct).toBe(3.0);
    expect(result.max_risk_pct).toBe(10);
    expect(result.frozen).toBe(false);
    expect(result.positions).toHaveLength(2);
    expect(result.positions[0].symbol).toBe("RELIANCE");
  });
});

describe("getShadowComparison", () => {
  it("transforms shadow response and scales win rates", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      shadow_win_rate: 0.65,
      live_win_rate: 0.55,
      shadow_avg_r: 1.2,
      live_avg_r: 0.8,
      human_alpha: 0.4,
      verdict: "Shadow outperforming",
      approved_win_rate: 0.6,
      skipped_win_rate: 0.7,
      trades: [],
    }));

    const result = await getShadowComparison();

    // 0-1 ratios should be scaled to 0-100
    expect(result.shadow_win_rate).toBeCloseTo(65);
    expect(result.live_win_rate).toBeCloseTo(55);
    expect(result.approved_win_rate).toBeCloseTo(60);
    expect(result.skipped_win_rate).toBeCloseTo(70);
    expect(result.shadow_avg_r).toBe(1.2);
    expect(result.human_alpha).toBe(0.4);
  });

  it("does not scale already-percentage win rates", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      shadow_win_rate: 65,
      live_win_rate: 55,
      shadow_avg_r: 1.2,
      live_avg_r: 0.8,
      human_alpha: 0.4,
      verdict: "test",
      approved_win_rate: 60,
      skipped_win_rate: 70,
      trades: [],
    }));

    const result = await getShadowComparison();

    expect(result.shadow_win_rate).toBe(65);
    expect(result.live_win_rate).toBe(55);
  });

  it("uses message as verdict fallback", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      message: "Not enough data",
      sufficient_data: false,
    }));

    const result = await getShadowComparison();

    expect(result.verdict).toBe("Not enough data");
  });
});

describe("getAttribution", () => {
  it("handles wrapped response {attribution: [...]}", async () => {
    mockFetch.mockResolvedValueOnce(okResponse({
      attribution: [
        {
          signal_type: "PPC",
          regime: "TRENDING_BULL",
          trade_count: 10,
          win_count: 7,
          win_rate: 0.7,
          avg_r: 1.5,
          total_r: 15,
        },
      ],
    }));

    const result = await getAttribution();

    expect(result).toHaveLength(1);
    expect(result[0].signal_type).toBe("PPC");
    expect(result[0].win_rate).toBe(70); // scaled from 0.7
  });

  it("handles bare array response", async () => {
    mockFetch.mockResolvedValueOnce(okResponse([
      {
        signal_type: "NPC",
        regime: "RANGING_QUIET",
        trade_count: 5,
        win_count: 2,
        win_rate: 40,
        avg_r: 0.8,
        total_r: 4,
      },
    ]));

    const result = await getAttribution();

    expect(result).toHaveLength(1);
    expect(result[0].win_rate).toBe(40); // already percentage, not scaled
  });
});

describe("getLearningProgress", () => {
  it("fetches learning progress data", async () => {
    const progressData = {
      loop_status: { closed: true, issues: [], description: "All good" },
      current_regime: {
        regime: "TRENDING_BULL",
        date: "2025-03-15",
        nifty_adx: 28,
        india_vix: 14,
        hurst_exponent: 0.6,
      },
      regime_banks: { active_regime: null, active_version: "v1", banks: {} },
      parameters: {},
      experiment_summary: {
        total_experiments: 0,
        keep_count: 0,
        revert_count: 0,
        error_count: 0,
        keep_rate_pct: 0,
        most_improved_parameter: null,
        best_score: null,
        latest_score: null,
        first_experiment: null,
        latest_experiment: null,
      },
      experiment_timeline: [],
      learning_velocity: {
        recent_keep_rate: 0,
        older_keep_rate: null,
        trend: "flat",
        total_experiments: 0,
      },
    };
    mockFetch.mockResolvedValueOnce(okResponse(progressData));

    const result = await getLearningProgress();

    expect(result).toEqual(progressData);
  });
});

describe("API error handling", () => {
  it("throws with status and body for non-ok responses", async () => {
    mockFetch.mockResolvedValueOnce(errResponse(422, '{"detail":"Validation error"}'));

    await expect(getRegime()).rejects.toThrow('API error 422: {"detail":"Validation error"}');
  });
});
