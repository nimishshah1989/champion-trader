"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createJournal, type JournalCreateRequest } from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GRAVE_OFFENCES = [
  { key: "grave_casual_trade", label: "Took a casual/unplanned trade" },
  { key: "grave_sl_violation", label: "Violated stop loss rules" },
  { key: "grave_risk_exceeded", label: "Exceeded maximum risk limit" },
  { key: "grave_averaged_down", label: "Averaged down on a losing position" },
  { key: "grave_rebought_loser", label: "Re-bought a stock that was previously stopped out" },
] as const;

type GraveKey = (typeof GRAVE_OFFENCES)[number]["key"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(value: number | null): string {
  if (value === null || value === undefined) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function getMondayOfCurrentWeek(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(now.setDate(diff));
  return monday.toISOString().split("T")[0];
}

function getFridayFromMonday(mondayStr: string): string {
  const d = new Date(mondayStr);
  d.setDate(d.getDate() + 4);
  return d.toISOString().split("T")[0];
}

const TEXT_AREA_CLASS =
  "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none resize-none";

// ---------------------------------------------------------------------------
// Form Component
// ---------------------------------------------------------------------------

export function NewJournalForm({
  onSaved,
  onCancel,
}: {
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [weekStart, setWeekStart] = useState(getMondayOfCurrentWeek());
  const [weekEnd, setWeekEnd] = useState(getFridayFromMonday(getMondayOfCurrentWeek()));
  const [accountStart, setAccountStart] = useState("");
  const [accountEnd, setAccountEnd] = useState("");
  const [graveState, setGraveState] = useState<Record<GraveKey, boolean>>({
    grave_casual_trade: false,
    grave_sl_violation: false,
    grave_risk_exceeded: false,
    grave_averaged_down: false,
    grave_rebought_loser: false,
  });
  const [excelledAt, setExcelledAt] = useState("");
  const [poorAt, setPoorAt] = useState("");
  const [keyLearnings, setKeyLearnings] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (weekStart) setWeekEnd(getFridayFromMonday(weekStart));
  }, [weekStart]);

  const hasGrave = Object.values(graveState).some(Boolean);

  const calculatedReturn = (() => {
    const s = parseFloat(accountStart);
    const e = parseFloat(accountEnd);
    if (!s || !e || s === 0) return null;
    return ((e - s) / s) * 100;
  })();

  async function handleSubmit() {
    if (!weekStart || !weekEnd) {
      toast.error("Week start and end dates are required");
      return;
    }
    setSubmitting(true);
    try {
      const payload: JournalCreateRequest = {
        week_start: weekStart,
        week_end: weekEnd,
        ...(accountStart ? { account_value_start: parseFloat(accountStart) } : {}),
        ...(accountEnd ? { account_value_end: parseFloat(accountEnd) } : {}),
        ...graveState,
        ...(excelledAt ? { excelled_at: excelledAt } : {}),
        ...(poorAt ? { poor_at: poorAt } : {}),
        ...(keyLearnings ? { key_learnings: keyLearnings } : {}),
      };
      await createJournal(payload);
      toast.success("Journal entry saved successfully");
      onSaved();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save journal";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  function toggleGrave(key: GraveKey) {
    setGraveState((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-800">New Weekly Review</h2>
        <Button variant="outline" onClick={onCancel} className="text-sm">Cancel</Button>
      </div>

      {/* Week & Account */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-4">Week & Account</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="ws" className="text-sm text-slate-500">Week Start (Monday)</Label>
            <Input id="ws" type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="we" className="text-sm text-slate-500">Week End (Friday)</Label>
            <Input id="we" type="date" value={weekEnd} onChange={(e) => setWeekEnd(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="as" className="text-sm text-slate-500">Account Value Start</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">INR</span>
              <Input id="as" type="number" placeholder="0" value={accountStart} onChange={(e) => setAccountStart(e.target.value)} className="pl-12 font-mono" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ae" className="text-sm text-slate-500">Account Value End</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">INR</span>
              <Input id="ae" type="number" placeholder="0" value={accountEnd} onChange={(e) => setAccountEnd(e.target.value)} className="pl-12 font-mono" />
            </div>
          </div>
        </div>
        {calculatedReturn !== null && (
          <div className="mt-4 flex items-center gap-3 px-4 py-3 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-sm text-slate-500">Weekly Return:</span>
            <span className={`text-lg font-bold font-mono ${calculatedReturn >= 0 ? "text-emerald-600" : "text-red-600"}`}>
              {formatPct(calculatedReturn)}
            </span>
          </div>
        )}
      </div>

      {/* Grave Offences */}
      <div className={`bg-white rounded-xl border ${hasGrave ? "border-red-300" : "border-slate-200"} p-6`}>
        <h3 className="text-sm font-semibold text-slate-800 mb-1">Grave Mistakes</h3>
        <p className="text-xs text-slate-400 mb-4">Honest self-check. Any YES is a serious concern.</p>
        {hasGrave && (
          <div className="mb-4 px-4 py-2.5 rounded-lg bg-red-50 border border-red-200">
            <span className="text-sm font-semibold text-red-700">Grave mistakes detected -- review required</span>
          </div>
        )}
        <div className="space-y-1 divide-y divide-slate-100">
          {GRAVE_OFFENCES.map(({ key, label }) => (
            <label key={key} className="flex items-center justify-between py-2.5 cursor-pointer group">
              <span className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors">{label}</span>
              <button
                type="button"
                role="switch"
                aria-checked={graveState[key]}
                onClick={() => toggleGrave(key)}
                className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 ${graveState[key] ? "bg-red-500" : "bg-slate-200"}`}
              >
                <span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transform transition-transform duration-200 ${graveState[key] ? "translate-x-6" : "translate-x-1"}`} />
              </button>
            </label>
          ))}
        </div>
      </div>

      {/* Reflection */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-4">Reflection</h3>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="excelled" className="text-sm text-slate-500">What I excelled at this week</Label>
            <textarea id="excelled" value={excelledAt} onChange={(e) => setExcelledAt(e.target.value)} placeholder="Discipline, good entries, patience..." rows={3} className={TEXT_AREA_CLASS} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="poor" className="text-sm text-slate-500">What I was poor at this week</Label>
            <textarea id="poor" value={poorAt} onChange={(e) => setPoorAt(e.target.value)} placeholder="Chased entries, ignored signals..." rows={3} className={TEXT_AREA_CLASS} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="learnings" className="text-sm text-slate-500">Key learnings and action items</Label>
            <textarea id="learnings" value={keyLearnings} onChange={(e) => setKeyLearnings(e.target.value)} placeholder="Lessons, pattern observations, rule refinements..." rows={3} className={TEXT_AREA_CLASS} />
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="flex items-center gap-3">
        <Button onClick={handleSubmit} disabled={submitting} className="bg-teal-600 text-white hover:bg-teal-700">
          {submitting ? "Saving..." : "Save Journal Entry"}
        </Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}
