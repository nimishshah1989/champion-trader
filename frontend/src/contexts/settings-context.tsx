"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";

type Exchange = "NSE" | "BSE";
type Stance = "STRONG" | "MODERATE" | "WEAK";

export interface TradingSettings {
  accountValue: number;
  rptPct: number;
  exchange: Exchange;
  currentStance: Stance | null;
  maxPositions: number;
  stanceRptOverride: number | null;
}

interface SettingsContextValue {
  settings: TradingSettings;
  updateSettings: (patch: Partial<Omit<TradingSettings, "maxPositions">>) => void;
  effectiveRpt: number;
  resetToDefaults: () => void;
}

const STORAGE_KEY = "cts-trading-settings";
const STANCE_MAX_POSITIONS: Record<Stance, number> = { STRONG: 10, MODERATE: 6, WEAK: 4 };
const DEFAULT_MAX_POSITIONS = 6;

const DEFAULTS: TradingSettings = {
  accountValue: 500000,
  rptPct: 0.5,
  exchange: "NSE",
  currentStance: null,
  maxPositions: DEFAULT_MAX_POSITIONS,
  stanceRptOverride: null,
};

function deriveMaxPositions(stance: Stance | null): number {
  return stance ? STANCE_MAX_POSITIONS[stance] : DEFAULT_MAX_POSITIONS;
}

function loadFromStorage(): TradingSettings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<TradingSettings>;
    const stance = parsed.currentStance ?? null;
    return {
      accountValue: parsed.accountValue ?? DEFAULTS.accountValue,
      rptPct: parsed.rptPct ?? DEFAULTS.rptPct,
      exchange: parsed.exchange ?? DEFAULTS.exchange,
      currentStance: stance,
      maxPositions: deriveMaxPositions(stance),
      stanceRptOverride: parsed.stanceRptOverride ?? null,
    };
  } catch {
    return DEFAULTS;
  }
}

function persistToStorage(settings: TradingSettings): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    /* storage full or blocked */
  }
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<TradingSettings>(DEFAULTS);

  useEffect(() => {
    setSettings(loadFromStorage());
  }, []);

  const updateSettings = useCallback(
    (patch: Partial<Omit<TradingSettings, "maxPositions">>) => {
      setSettings((prev) => {
        const stance = patch.currentStance !== undefined ? patch.currentStance : prev.currentStance;
        const next: TradingSettings = {
          ...prev,
          ...patch,
          maxPositions: deriveMaxPositions(stance),
        };
        persistToStorage(next);
        return next;
      });
    },
    [],
  );

  const resetToDefaults = useCallback(() => {
    setSettings(DEFAULTS);
    persistToStorage(DEFAULTS);
  }, []);

  const effectiveRpt = settings.stanceRptOverride ?? settings.rptPct;

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, effectiveRpt, resetToDefaults }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used within a <SettingsProvider>");
  }
  return ctx;
}
