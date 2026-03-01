"use client";

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import {
  getLatestStance,
  getStanceHistory,
  logMarketStance,
  type MarketStance,
} from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoBanner, Term } from "@/components/info-banner";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NSE_SECTORS = [
  "Auto",
  "Bank",
  "Energy",
  "FMCG",
  "IT",
  "Media",
  "Metal",
  "Pharma",
  "PSU Bank",
  "Realty",
  "Infra",
  "Commodities",
  "Consumption",
  "Financial Services",
  "Healthcare",
  "MNC",
  "Private Bank",
  "PSE",
  "SME",
] as const;

const STANCE_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; rptRange: string; maxPos: string }
> = {
  STRONG: {
    label: "STRONG",
    color: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    rptRange: "0.50% – 0.80%",
    maxPos: "8–10",
  },
  MODERATE: {
    label: "MODERATE",
    color: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
    rptRange: "0.30% – 0.50%",
    maxPos: "5–6",
  },
  WEAK: {
    label: "WEAK",
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
    rptRange: "0.20%",
    maxPos: "3–4",
  },
};

function deriveStance(strongCount: number, weakCount: number): string {
  if (strongCount >= 3 && weakCount <= 1) return "STRONG";
  if (weakCount >= 3 && strongCount <= 1) return "WEAK";
  return "MODERATE";
}

function deriveRpt(stance: string): number {
  if (stance === "STRONG") return 0.5;
  if (stance === "WEAK") return 0.2;
  return 0.35;
}

function deriveMaxPositions(stance: string): number {
  if (stance === "STRONG") return 10;
  if (stance === "WEAK") return 4;
  return 6;
}

// ---------------------------------------------------------------------------
// Sector Picker
// ---------------------------------------------------------------------------

function SectorPicker({
  label,
  selected,
  onToggle,
  colorClass,
}: {
  label: string;
  selected: Set<string>;
  onToggle: (sector: string) => void;
  colorClass: string;
}) {
  return (
    <div>
      <label className="text-xs text-slate-500 font-medium mb-2 block">{label}</label>
      <div className="flex flex-wrap gap-1.5">
        {NSE_SECTORS.map((sector) => {
          const isActive = selected.has(sector);
          return (
            <button
              key={sector}
              type="button"
              onClick={() => onToggle(sector)}
              className={`text-[11px] font-medium px-2.5 py-1 rounded-full border transition-all ${
                isActive
                  ? `${colorClass} border-current`
                  : "bg-white text-slate-400 border-slate-200 hover:border-slate-300"
              }`}
            >
              {sector}
            </button>
          );
        })}
      </div>
      <p className="text-[10px] text-slate-400 mt-1">{selected.size} selected</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function MarketStancePage() {
  const [latest, setLatest] = useState<MarketStance | null>(null);
  const [history, setHistory] = useState<MarketStance[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [strongSectors, setStrongSectors] = useState<Set<string>>(new Set());
  const [weakSectors, setWeakSectors] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const derivedStance = deriveStance(strongSectors.size, weakSectors.size);
  const derivedRpt = deriveRpt(derivedStance);
  const derivedMaxPos = deriveMaxPositions(derivedStance);
  const stanceConfig = STANCE_CONFIG[derivedStance];

  const fetchData = useCallback(async () => {
    try {
      const [latestData, historyData] = await Promise.all([
        getLatestStance(),
        getStanceHistory(30),
      ]);
      setLatest(latestData);
      setHistory(historyData);
    } catch (err) {
      toast.error("Failed to load market stance data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function toggleSector(set: Set<string>, setter: (s: Set<string>) => void, sector: string) {
    const next = new Set(set);
    if (next.has(sector)) {
      next.delete(sector);
    } else {
      next.add(sector);
    }
    setter(next);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const today = new Date().toISOString().split("T")[0];
      await logMarketStance({
        log_date: today,
        strong_sectors: Array.from(strongSectors),
        weak_sectors: Array.from(weakSectors),
        stance: derivedStance,
        rpt_pct: derivedRpt,
        max_positions: derivedMaxPos,
        notes: notes || undefined,
      });
      toast.success(`Market stance logged: ${derivedStance}`);
      setShowForm(false);
      setStrongSectors(new Set());
      setWeakSectors(new Set());
      setNotes("");
      await fetchData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to log stance";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  // Current stance display
  const currentStance = latest?.stance ?? null;
  const currentConfig = currentStance ? STANCE_CONFIG[currentStance] : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Market Stance</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Daily sector strength assessment — drives RPT% and position limits
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm"
          >
            Log Today&apos;s Stance
          </button>
        )}
      </div>

      <InfoBanner title="Quick Reference — Market Stance" storageKey="market-stance">
        <Term label="Market Stance">Daily assessment of sector strength. Count sectors showing PPC dominance vs NPC dominance.</Term>
        <Term label="STRONG (6+ strong sectors)">Aggressive: RPT 0.5-0.8%, up to 10 positions.</Term>
        <Term label="MODERATE (3-5 strong)">Normal: RPT 0.3-0.5%, up to 6 positions.</Term>
        <Term label="WEAK (0-2 strong)">Defensive: RPT 0.2%, max 4 positions.</Term>
        <p className="text-slate-500 italic">Stance drives position sizing and exposure — trade smaller in weak markets, bigger in strong markets.</p>
      </InfoBanner>

      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Current Stance</p>
          {loading ? (
            <Skeleton className="h-8 w-24 bg-slate-100" />
          ) : currentConfig ? (
            <span className={`text-2xl font-bold ${currentConfig.color}`}>
              {currentConfig.label}
            </span>
          ) : (
            <span className="text-2xl font-bold text-slate-300">—</span>
          )}
          {latest && (
            <p className="text-[10px] text-slate-400 mt-1">
              as of {new Date(latest.log_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
            </p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Suggested RPT%</p>
          {loading ? (
            <Skeleton className="h-8 w-20 bg-slate-100" />
          ) : (
            <span className="text-2xl font-bold text-slate-800 font-mono">
              {latest?.rpt_pct != null ? `${latest.rpt_pct}%` : "0.50%"}
            </span>
          )}
          <p className="text-[10px] text-slate-400 mt-1">
            {currentStance ? STANCE_CONFIG[currentStance]?.rptRange : "Range: 0.20% – 0.80%"}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Max Positions</p>
          {loading ? (
            <Skeleton className="h-8 w-16 bg-slate-100" />
          ) : (
            <span className="text-2xl font-bold text-slate-800 font-mono">
              {latest?.max_positions ?? "—"}
            </span>
          )}
          <p className="text-[10px] text-slate-400 mt-1">
            Weak: 3-4 | Mod: 5-6 | Strong: 8-10
          </p>
        </div>
      </div>

      {/* Log form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-teal-500 p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-slate-800">Log Today&apos;s Market Stance</h3>
            <button
              onClick={() => setShowForm(false)}
              className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
            >
              Cancel
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Sector pickers */}
            <SectorPicker
              label="Strong Sectors (showing PPC dominance)"
              selected={strongSectors}
              onToggle={(s) => toggleSector(strongSectors, setStrongSectors, s)}
              colorClass="bg-emerald-100 text-emerald-700"
            />
            <SectorPicker
              label="Weak Sectors (showing NPC dominance)"
              selected={weakSectors}
              onToggle={(s) => toggleSector(weakSectors, setWeakSectors, s)}
              colorClass="bg-red-100 text-red-700"
            />

            {/* Auto-derived stance preview */}
            <div className={`${stanceConfig.bg} ${stanceConfig.border} border rounded-xl p-4`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Auto-classified Stance</p>
                  <span className={`text-lg font-bold ${stanceConfig.color}`}>{derivedStance}</span>
                </div>
                <div className="text-right text-xs space-y-1">
                  <div>
                    <span className="text-slate-400">RPT%: </span>
                    <span className="font-mono font-semibold text-slate-700">{derivedRpt}%</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Max Positions: </span>
                    <span className="font-mono font-semibold text-slate-700">{derivedMaxPos}</span>
                  </div>
                  <div>
                    <span className="text-emerald-600 font-mono">{strongSectors.size} strong</span>
                    <span className="text-slate-300 mx-1">|</span>
                    <span className="text-red-600 font-mono">{weakSectors.size} weak</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="text-xs text-slate-500 font-medium mb-1 block">Notes</label>
              <input
                type="text"
                placeholder="Market observations, events, FII/DII data..."
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="bg-teal-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
            >
              {submitting ? "Saving..." : "Log Stance"}
            </button>
          </form>
        </div>
      )}

      {/* History table */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-800">Stance History (Last 30 Days)</h3>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-5 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-8 w-full bg-slate-100" />
              ))}
            </div>
          ) : history.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm text-slate-400">No stance history yet. Log your first stance above.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="px-5 py-3 font-medium">Date</th>
                  <th className="px-5 py-3 font-medium">Stance</th>
                  <th className="px-5 py-3 font-medium">Strong</th>
                  <th className="px-5 py-3 font-medium">Weak</th>
                  <th className="px-5 py-3 font-medium">RPT%</th>
                  <th className="px-5 py-3 font-medium">Max Pos</th>
                  <th className="px-5 py-3 font-medium">Notes</th>
                </tr>
              </thead>
              <tbody>
                {history.map((entry) => {
                  const config = entry.stance ? STANCE_CONFIG[entry.stance] : null;
                  return (
                    <tr key={entry.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                      <td className="px-5 py-3 font-mono text-xs text-slate-600">
                        {new Date(entry.log_date).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          weekday: "short",
                        })}
                      </td>
                      <td className="px-5 py-3">
                        {config ? (
                          <span className={`${config.bg} ${config.color} ${config.border} border rounded-full px-2.5 py-0.5 text-[11px] font-bold`}>
                            {config.label}
                          </span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <span className="font-mono text-xs text-emerald-600 font-semibold">{entry.strong_count ?? 0}</span>
                        {entry.strong_sectors && (
                          <span className="text-[10px] text-slate-400 ml-1">
                            ({entry.strong_sectors.split(",").slice(0, 3).join(", ")}
                            {(entry.strong_sectors.split(",").length > 3) ? "..." : ""})
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <span className="font-mono text-xs text-red-600 font-semibold">{entry.weak_count ?? 0}</span>
                        {entry.weak_sectors && (
                          <span className="text-[10px] text-slate-400 ml-1">
                            ({entry.weak_sectors.split(",").slice(0, 3).join(", ")}
                            {(entry.weak_sectors.split(",").length > 3) ? "..." : ""})
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs font-semibold text-slate-700">
                        {entry.rpt_pct != null ? `${entry.rpt_pct}%` : "—"}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-slate-700">
                        {entry.max_positions ?? "—"}
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-500 max-w-[200px] truncate">
                        {entry.notes || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
