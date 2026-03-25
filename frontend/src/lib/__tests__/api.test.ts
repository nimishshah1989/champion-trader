import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { Mock } from "vitest";

// We need to mock fetch before importing the module
const mockFetch = vi.fn() as Mock;
vi.stubGlobal("fetch", mockFetch);

// Dynamic import so fetch is already stubbed
const apiModule = await import("../api");
const {
  healthCheck,
  getScanResults,
  getWatchlist,
  getTrades,
  getTradeStats,
  calculatePosition,
  getAlerts,
  getUnreadAlertCount,
  markAlertRead,
  markAllAlertsRead,
  getSimulationRuns,
} = apiModule;

function mockJsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
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

function mockErrorResponse(status: number, body: string): Response {
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

describe("healthCheck", () => {
  it("fetches /health and returns parsed data", async () => {
    const healthData = {
      status: "ok",
      scheduler: "running" as const,
      scheduled_jobs: 3,
      jobs: [],
    };
    mockFetch.mockResolvedValueOnce(mockJsonResponse(healthData));

    const result = await healthCheck();

    expect(result).toEqual(healthData);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws on API error responses", async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(500, "Internal Server Error"));

    await expect(healthCheck()).rejects.toThrow("API error 500: Internal Server Error");
  });
});

describe("getScanResults", () => {
  it("fetches without params", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getScanResults();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/scanner/results",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("includes query params when provided", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getScanResults("2025-03-15", "PPC");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/scanner/results?scan_date=2025-03-15&scan_type=PPC",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

describe("getWatchlist", () => {
  it("fetches the watchlist", async () => {
    const items = [{ id: 1, symbol: "RELIANCE", bucket: "READY", status: "active" }];
    mockFetch.mockResolvedValueOnce(mockJsonResponse(items));

    const result = await getWatchlist();

    expect(result).toEqual(items);
  });
});

describe("getTrades", () => {
  it("fetches trades without filter", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getTrades();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/trades",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("adds status filter", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getTrades("open");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/trades?status=open",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

describe("getTradeStats", () => {
  it("fetches trade stats", async () => {
    const stats = {
      total_trades: 10,
      open_trades: 2,
      closed_trades: 8,
      win_count: 5,
      loss_count: 3,
      win_rate: 62.5,
      avg_r_multiple: 1.5,
      arr: 0.85,
      total_pnl: 25000,
    };
    mockFetch.mockResolvedValueOnce(mockJsonResponse(stats));

    const result = await getTradeStats();

    expect(result).toEqual(stats);
  });
});

describe("calculatePosition", () => {
  it("sends POST with position calc data", async () => {
    const request = {
      symbol: "ASTERDM",
      account_value: 500000,
      rpt_pct: 0.5,
      entry_price: 601,
      trp_pct: 3.18,
    };
    const response = {
      rpt_amount: 2500,
      sl_price: 581.9,
      sl_pct: 3.18,
      sl_amount: 19.1,
      position_value: 78731,
      position_size: 131,
      half_qty: 65,
      target_2r: 639.2,
      target_ne: 677.44,
      target_ge: 753.88,
      target_ee: 830.32,
    };
    mockFetch.mockResolvedValueOnce(mockJsonResponse(response));

    const result = await calculatePosition(request);

    expect(result).toEqual(response);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/calculator/position",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
      }),
    );
  });
});

describe("alert API functions", () => {
  it("getAlerts fetches all alerts", async () => {
    const alerts = [{ id: 1, title: "Test", severity: "info" }];
    mockFetch.mockResolvedValueOnce(mockJsonResponse(alerts));

    const result = await getAlerts();

    expect(result).toEqual(alerts);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/alerts",
      expect.any(Object),
    );
  });

  it("getAlerts with unreadOnly passes query param", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getAlerts(true);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/alerts?unread_only=true",
      expect.any(Object),
    );
  });

  it("getUnreadAlertCount returns count", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ count: 5 }));

    const result = await getUnreadAlertCount();

    expect(result).toEqual({ count: 5 });
  });

  it("markAlertRead sends PATCH", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ message: "ok" }));

    await markAlertRead(42);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/alerts/42/read",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("markAllAlertsRead sends PATCH", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ message: "ok" }));

    await markAllAlertsRead();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/alerts/read-all",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

describe("getSimulationRuns", () => {
  it("fetches without filter", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getSimulationRuns();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/simulation/runs",
      expect.any(Object),
    );
  });

  it("adds run_type filter", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([]));

    await getSimulationRuns("backtest");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/simulation/runs?run_type=backtest",
      expect.any(Object),
    );
  });
});

describe("error handling", () => {
  it("includes status code and body in error message", async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(404, "Not Found"));

    await expect(getWatchlist()).rejects.toThrow("API error 404: Not Found");
  });

  it("handles network errors", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(healthCheck()).rejects.toThrow("Failed to fetch");
  });
});
