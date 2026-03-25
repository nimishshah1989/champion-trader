import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { SettingsProvider, useSettings } from "../settings-context";
import type { TradingSettings } from "../settings-context";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Test component that displays settings
function SettingsDisplay() {
  const { settings, effectiveRpt } = useSettings();
  return (
    <div>
      <span data-testid="accountValue">{settings.accountValue}</span>
      <span data-testid="rptPct">{settings.rptPct}</span>
      <span data-testid="exchange">{settings.exchange}</span>
      <span data-testid="maxPositions">{settings.maxPositions}</span>
      <span data-testid="effectiveRpt">{effectiveRpt}</span>
      <span data-testid="stance">{settings.currentStance ?? "none"}</span>
    </div>
  );
}

// Test component that updates settings
function SettingsUpdater() {
  const { settings, updateSettings, resetToDefaults } = useSettings();
  return (
    <div>
      <span data-testid="accountValue">{settings.accountValue}</span>
      <span data-testid="maxPositions">{settings.maxPositions}</span>
      <span data-testid="stance">{settings.currentStance ?? "none"}</span>
      <button
        data-testid="updateAccount"
        onClick={() => updateSettings({ accountValue: 1000000 })}
      />
      <button
        data-testid="setStance"
        onClick={() => updateSettings({ currentStance: "STRONG" })}
      />
      <button data-testid="reset" onClick={resetToDefaults} />
    </div>
  );
}

beforeEach(() => {
  localStorageMock.clear();
  vi.clearAllMocks();
});

describe("SettingsProvider", () => {
  it("renders children and provides default settings", () => {
    render(
      <SettingsProvider>
        <SettingsDisplay />
      </SettingsProvider>,
    );

    expect(screen.getByTestId("accountValue").textContent).toBe("500000");
    expect(screen.getByTestId("rptPct").textContent).toBe("0.5");
    expect(screen.getByTestId("exchange").textContent).toBe("NSE");
    expect(screen.getByTestId("maxPositions").textContent).toBe("6");
    expect(screen.getByTestId("effectiveRpt").textContent).toBe("0.5");
  });

  it("loads settings from localStorage on mount", async () => {
    const saved: Partial<TradingSettings> = {
      accountValue: 750000,
      rptPct: 0.75,
      exchange: "BSE",
      currentStance: "STRONG",
    };
    localStorageMock.setItem("cts-trading-settings", JSON.stringify(saved));

    render(
      <SettingsProvider>
        <SettingsDisplay />
      </SettingsProvider>,
    );

    // After useEffect runs, localStorage values should be applied
    // Wait for the effect
    await act(async () => {});

    expect(screen.getByTestId("accountValue").textContent).toBe("750000");
    expect(screen.getByTestId("exchange").textContent).toBe("BSE");
    expect(screen.getByTestId("stance").textContent).toBe("STRONG");
    expect(screen.getByTestId("maxPositions").textContent).toBe("10"); // STRONG = 10
  });

  it("uses effectiveRpt from stanceRptOverride when set", async () => {
    const saved: Partial<TradingSettings> = {
      rptPct: 0.5,
      stanceRptOverride: 0.3,
    };
    localStorageMock.setItem("cts-trading-settings", JSON.stringify(saved));

    render(
      <SettingsProvider>
        <SettingsDisplay />
      </SettingsProvider>,
    );

    await act(async () => {});

    expect(screen.getByTestId("effectiveRpt").textContent).toBe("0.3");
  });

  it("updates settings and persists to localStorage", async () => {
    render(
      <SettingsProvider>
        <SettingsUpdater />
      </SettingsProvider>,
    );

    await act(async () => {
      screen.getByTestId("updateAccount").click();
    });

    expect(screen.getByTestId("accountValue").textContent).toBe("1000000");
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "cts-trading-settings",
      expect.stringContaining("1000000"),
    );
  });

  it("derives maxPositions from stance", async () => {
    render(
      <SettingsProvider>
        <SettingsUpdater />
      </SettingsProvider>,
    );

    await act(async () => {
      screen.getByTestId("setStance").click();
    });

    expect(screen.getByTestId("stance").textContent).toBe("STRONG");
    expect(screen.getByTestId("maxPositions").textContent).toBe("10");
  });

  it("resets to defaults", async () => {
    const saved: Partial<TradingSettings> = {
      accountValue: 999999,
      rptPct: 1.0,
    };
    localStorageMock.setItem("cts-trading-settings", JSON.stringify(saved));

    render(
      <SettingsProvider>
        <SettingsUpdater />
      </SettingsProvider>,
    );

    await act(async () => {});
    await act(async () => {
      screen.getByTestId("reset").click();
    });

    expect(screen.getByTestId("accountValue").textContent).toBe("500000");
  });

  it("handles corrupted localStorage gracefully", async () => {
    localStorageMock.setItem("cts-trading-settings", "not-valid-json{{{");

    // Should not throw, falls back to defaults
    render(
      <SettingsProvider>
        <SettingsDisplay />
      </SettingsProvider>,
    );

    await act(async () => {});

    expect(screen.getByTestId("accountValue").textContent).toBe("500000");
  });
});

describe("useSettings outside provider", () => {
  it("throws when used without SettingsProvider", () => {
    function BadComponent() {
      useSettings();
      return <div />;
    }

    // Suppress console.error for this test
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<BadComponent />)).toThrow(
      "useSettings must be used within a <SettingsProvider>",
    );

    spy.mockRestore();
  });
});
