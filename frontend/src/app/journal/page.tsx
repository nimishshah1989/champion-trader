"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getJournals,
  createJournal,
  type Journal,
  type JournalCreateRequest,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatINR(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPct(value: number | null): string {
  if (value === null || value === undefined) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function truncate(text: string | null, maxLen: number): string {
  if (!text) return "--";
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + "...";
}

function formatWeekRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${s.toLocaleDateString("en-IN", opts)} - ${e.toLocaleDateString("en-IN", opts)}, ${e.getFullYear()}`;
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

// ---------------------------------------------------------------------------
// Toggle Switch Component
// ---------------------------------------------------------------------------

function ToggleSwitch({
  checked,
  onChange,
  label,
  accentColor = "teal",
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  label: string;
  accentColor?: "teal" | "red" | "emerald";
}) {
  const bgOn =
    accentColor === "red"
      ? "bg-red-500"
      : accentColor === "emerald"
        ? "bg-emerald-500"
        : "bg-teal-600";

  return (
    <label className="flex items-center justify-between py-2 cursor-pointer group">
      <span className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 ${
          checked ? bgOn : "bg-slate-200"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transform transition-transform duration-200 ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Section Wrapper Component
// ---------------------------------------------------------------------------

function FormSection({
  title,
  sectionNumber,
  borderColor = "border-slate-200",
  children,
  defaultOpen = true,
}: {
  title: string;
  sectionNumber: number;
  borderColor?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`bg-white rounded-xl border ${borderColor} overflow-hidden`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50/50 transition-colors"
      >
        <h3 className="text-base font-semibold text-slate-800">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-slate-100 text-xs font-bold text-slate-600 mr-2">
            {sectionNumber}
          </span>
          {title}
        </h3>
        <svg
          className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 pb-6">
          <Separator className="mb-5" />
          {children}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Text Area Component
// ---------------------------------------------------------------------------

function TextArea({
  id,
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-sm text-slate-500">
        {label}
      </Label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none resize-none"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton Loader for History Table
// ---------------------------------------------------------------------------

function JournalTableSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <Skeleton className="h-6 w-48 bg-slate-100" />
        <Skeleton className="h-5 w-24 bg-slate-100" />
      </div>
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, idx) => (
          <div key={idx} className="flex items-center gap-4">
            <Skeleton className="h-4 w-32 bg-slate-100" />
            <Skeleton className="h-4 w-20 bg-slate-100" />
            <Skeleton className="h-4 w-20 bg-slate-100" />
            <Skeleton className="h-4 w-16 bg-slate-100" />
            <Skeleton className="h-4 w-12 bg-slate-100" />
            <Skeleton className="h-4 w-16 bg-slate-100" />
            <Skeleton className="h-4 w-12 bg-slate-100" />
            <Skeleton className="h-4 flex-1 bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty State
// ---------------------------------------------------------------------------

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 mb-4">
        <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
          />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-slate-800 mb-1">No journal entries yet</h3>
      <p className="text-sm text-slate-500 mb-4 max-w-md mx-auto">
        Start your weekly self-review process. Each journal entry covers grave mistakes,
        risk management, technical review, routine adherence, and psychology.
      </p>
      <Button
        onClick={onNew}
        className="bg-teal-600 text-white hover:bg-teal-700"
      >
        + New Journal Entry
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expanded Journal Detail View
// ---------------------------------------------------------------------------

function JournalDetail({ journal }: { journal: Journal }) {
  return (
    <tr>
      <td colSpan={8} className="px-4 py-4 bg-slate-50">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Excelled At
            </p>
            <p className="text-sm text-slate-700">{journal.excelled_at || "--"}</p>
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Poor At
            </p>
            <p className="text-sm text-slate-700">{journal.poor_at || "--"}</p>
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Key Learnings
            </p>
            <p className="text-sm text-slate-700">{journal.key_learnings || "--"}</p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4 mt-4">
          <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
            <p className="text-xs text-slate-400">Trades Taken</p>
            <p className="text-lg font-bold font-mono text-slate-800">
              {journal.trades_taken ?? "--"}
            </p>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
            <p className="text-xs text-slate-400">Wins / Losses</p>
            <p className="text-lg font-bold font-mono text-slate-800">
              <span className="text-emerald-600">{journal.win_count ?? 0}</span>
              {" / "}
              <span className="text-red-600">{journal.loss_count ?? 0}</span>
            </p>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
            <p className="text-xs text-slate-400">Win Rate</p>
            <p
              className={`text-lg font-bold font-mono ${
                (journal.win_rate ?? 0) >= 40 ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {journal.win_rate !== null ? `${journal.win_rate.toFixed(1)}%` : "--"}
            </p>
          </div>
          <div className="bg-white rounded-lg border border-slate-200 p-3 text-center">
            <p className="text-xs text-slate-400">ARR</p>
            <p
              className={`text-lg font-bold font-mono ${
                (journal.arr ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {journal.arr !== null ? journal.arr.toFixed(2) : "--"}
            </p>
          </div>
        </div>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function JournalPage() {
  // State: data loading
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State: UI
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // State: Form fields
  const [weekStart, setWeekStart] = useState(getMondayOfCurrentWeek());
  const [weekEnd, setWeekEnd] = useState(getFridayFromMonday(getMondayOfCurrentWeek()));
  const [accountStart, setAccountStart] = useState<string>("");
  const [accountEnd, setAccountEnd] = useState<string>("");

  // Grave mistakes
  const [graveCasual, setGraveCasual] = useState(false);
  const [graveSl, setGraveSl] = useState(false);
  const [graveRisk, setGraveRisk] = useState(false);
  const [graveAveraged, setGraveAveraged] = useState(false);
  const [graveRebought, setGraveRebought] = useState(false);

  // Risk management
  const [rmWinrateArr, setRmWinrateArr] = useState("");
  const [rmStanceAccuracy, setRmStanceAccuracy] = useState("");
  const [rmRptConsistency, setRmRptConsistency] = useState("");
  const [rmOrViolated, setRmOrViolated] = useState(false);
  const [rmSlippage, setRmSlippage] = useState("");
  const [rmStreak, setRmStreak] = useState("");

  // Technical
  const [techRandom, setTechRandom] = useState("");
  const [techPoorSetups, setTechPoorSetups] = useState("");
  const [techEntryTiming, setTechEntryTiming] = useState("");
  const [techSlPlacement, setTechSlPlacement] = useState("");
  const [techExitFramework, setTechExitFramework] = useState("");
  const [techExtension, setTechExtension] = useState("");
  const [techEarnings, setTechEarnings] = useState("");

  // Routine
  const [routineScans, setRoutineScans] = useState(true);
  const [routineWatchlist, setRoutineWatchlist] = useState(true);
  const [routineSetupTracker, setRoutineSetupTracker] = useState(true);
  const [routineScreenTime, setRoutineScreenTime] = useState(true);
  const [routineHistorical, setRoutineHistorical] = useState("");

  // Psychology
  const [psychAffirmations, setPsychAffirmations] = useState(true);
  const [psychImpulsive, setPsychImpulsive] = useState("");
  const [psychFearGreed, setPsychFearGreed] = useState("");
  const [psychSocialTrading, setPsychSocialTrading] = useState(false);
  const [psychStress, setPsychStress] = useState("LOW");

  // Summary
  const [excelledAt, setExcelledAt] = useState("");
  const [poorAt, setPoorAt] = useState("");
  const [keyLearnings, setKeyLearnings] = useState("");

  // Derived
  const hasGraveMistake = graveCasual || graveSl || graveRisk || graveAveraged || graveRebought;

  const calculatedReturn = (() => {
    const start = parseFloat(accountStart);
    const end = parseFloat(accountEnd);
    if (!start || !end || start === 0) return null;
    return ((end - start) / start) * 100;
  })();

  // Data fetch
  const fetchJournals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJournals();
      setJournals(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load journals";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJournals();
  }, [fetchJournals]);

  // Auto-compute week_end when week_start changes
  useEffect(() => {
    if (weekStart) {
      setWeekEnd(getFridayFromMonday(weekStart));
    }
  }, [weekStart]);

  // Reset form
  function resetForm() {
    setWeekStart(getMondayOfCurrentWeek());
    setWeekEnd(getFridayFromMonday(getMondayOfCurrentWeek()));
    setAccountStart("");
    setAccountEnd("");
    setGraveCasual(false);
    setGraveSl(false);
    setGraveRisk(false);
    setGraveAveraged(false);
    setGraveRebought(false);
    setRmWinrateArr("");
    setRmStanceAccuracy("");
    setRmRptConsistency("");
    setRmOrViolated(false);
    setRmSlippage("");
    setRmStreak("");
    setTechRandom("");
    setTechPoorSetups("");
    setTechEntryTiming("");
    setTechSlPlacement("");
    setTechExitFramework("");
    setTechExtension("");
    setTechEarnings("");
    setRoutineScans(true);
    setRoutineWatchlist(true);
    setRoutineSetupTracker(true);
    setRoutineScreenTime(true);
    setRoutineHistorical("");
    setPsychAffirmations(true);
    setPsychImpulsive("");
    setPsychFearGreed("");
    setPsychSocialTrading(false);
    setPsychStress("LOW");
    setExcelledAt("");
    setPoorAt("");
    setKeyLearnings("");
  }

  // Submit journal
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
        grave_casual_trade: graveCasual,
        grave_sl_violation: graveSl,
        grave_risk_exceeded: graveRisk,
        grave_averaged_down: graveAveraged,
        grave_rebought_loser: graveRebought,
        ...(rmWinrateArr ? { rm_winrate_arr_eval: rmWinrateArr } : {}),
        ...(rmStanceAccuracy ? { rm_market_stance_accuracy: rmStanceAccuracy } : {}),
        ...(rmRptConsistency ? { rm_rpt_consistency: rmRptConsistency } : {}),
        rm_or_matrix_violated: rmOrViolated,
        ...(rmSlippage ? { rm_slippage_issues: rmSlippage } : {}),
        ...(rmStreak ? { rm_streak_handling: rmStreak } : {}),
        ...(techRandom ? { tech_random_trades: techRandom } : {}),
        ...(techPoorSetups ? { tech_poor_setups: techPoorSetups } : {}),
        ...(techEntryTiming ? { tech_entry_timing: techEntryTiming } : {}),
        ...(techSlPlacement ? { tech_sl_placement: techSlPlacement } : {}),
        ...(techExitFramework ? { tech_exit_framework: techExitFramework } : {}),
        ...(techExtension ? { tech_extension_judgment: techExtension } : {}),
        ...(techEarnings ? { tech_earnings_handling: techEarnings } : {}),
        routine_scans_daily: routineScans,
        routine_watchlist_updated: routineWatchlist,
        routine_setup_tracker_updated: routineSetupTracker,
        routine_screen_time_minimised: routineScreenTime,
        ...(routineHistorical ? { routine_historical_analysis: routineHistorical } : {}),
        psych_affirmations_read: psychAffirmations,
        ...(psychImpulsive ? { psych_impulsive_actions: psychImpulsive } : {}),
        ...(psychFearGreed ? { psych_fear_greed_influence: psychFearGreed } : {}),
        psych_social_trading_influence: psychSocialTrading,
        psych_stress_level: psychStress,
        ...(excelledAt ? { excelled_at: excelledAt } : {}),
        ...(poorAt ? { poor_at: poorAt } : {}),
        ...(keyLearnings ? { key_learnings: keyLearnings } : {}),
      };

      await createJournal(payload);
      toast.success("Journal entry saved successfully");
      resetForm();
      setShowForm(false);
      fetchJournals();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save journal";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  // Routine adherence score
  const routineScore = [routineScans, routineWatchlist, routineSetupTracker, routineScreenTime].filter(
    Boolean,
  ).length;

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------------------------- */}
      {/* Page Header                                                      */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">
            Weekly Journal
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Champion Journal -- structured weekly self-review
          </p>
        </div>
        {!showForm && (
          <Button
            onClick={() => setShowForm(true)}
            className="bg-teal-600 text-white hover:bg-teal-700"
          >
            + New Journal Entry
          </Button>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* New Journal Form                                                 */}
      {/* ---------------------------------------------------------------- */}
      {showForm && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-800">
              New Weekly Review
            </h2>
            <Button
              variant="outline"
              onClick={() => {
                setShowForm(false);
                resetForm();
              }}
              className="text-sm"
            >
              Cancel
            </Button>
          </div>

          {/* Section 1: Week & Account */}
          <FormSection title="Week & Account" sectionNumber={1}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="week-start" className="text-sm text-slate-500">
                  Week Start (Monday)
                </Label>
                <Input
                  id="week-start"
                  type="date"
                  value={weekStart}
                  onChange={(e) => setWeekStart(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="week-end" className="text-sm text-slate-500">
                  Week End (Friday)
                </Label>
                <Input
                  id="week-end"
                  type="date"
                  value={weekEnd}
                  onChange={(e) => setWeekEnd(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="account-start" className="text-sm text-slate-500">
                  Account Value Start
                </Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">
                    INR
                  </span>
                  <Input
                    id="account-start"
                    type="number"
                    placeholder="0"
                    value={accountStart}
                    onChange={(e) => setAccountStart(e.target.value)}
                    className="pl-12 font-mono"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="account-end" className="text-sm text-slate-500">
                  Account Value End
                </Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">
                    INR
                  </span>
                  <Input
                    id="account-end"
                    type="number"
                    placeholder="0"
                    value={accountEnd}
                    onChange={(e) => setAccountEnd(e.target.value)}
                    className="pl-12 font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Calculated Return */}
            {calculatedReturn !== null && (
              <div className="mt-4 flex items-center gap-3 px-4 py-3 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-sm text-slate-500">Weekly Return:</span>
                <span
                  className={`text-lg font-bold font-mono ${
                    calculatedReturn >= 0 ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {formatPct(calculatedReturn)}
                </span>
                {accountStart && accountEnd && (
                  <span className="text-xs text-slate-400 ml-auto">
                    {formatINR(parseFloat(accountEnd) - parseFloat(accountStart))} P&L
                  </span>
                )}
              </div>
            )}
          </FormSection>

          {/* Section 2: Grave Mistakes */}
          <FormSection
            title="Grave Mistakes"
            sectionNumber={2}
            borderColor={hasGraveMistake ? "border-red-300" : "border-slate-200"}
          >
            {hasGraveMistake && (
              <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-red-600 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
                <span className="text-sm font-semibold text-red-700">
                  GRAVE MISTAKES DETECTED -- Serious review required
                </span>
              </div>
            )}
            <div className="space-y-1 divide-y divide-slate-100">
              <ToggleSwitch
                checked={graveCasual}
                onChange={setGraveCasual}
                label="Took a casual / random trade"
                accentColor="red"
              />
              <ToggleSwitch
                checked={graveSl}
                onChange={setGraveSl}
                label="Violated stop loss"
                accentColor="red"
              />
              <ToggleSwitch
                checked={graveRisk}
                onChange={setGraveRisk}
                label="Exceeded risk limits"
                accentColor="red"
              />
              <ToggleSwitch
                checked={graveAveraged}
                onChange={setGraveAveraged}
                label="Averaged down on a loser"
                accentColor="red"
              />
              <ToggleSwitch
                checked={graveRebought}
                onChange={setGraveRebought}
                label="Rebought a recent loser"
                accentColor="red"
              />
            </div>
          </FormSection>

          {/* Section 3: Risk Management */}
          <FormSection title="Risk Management" sectionNumber={3}>
            <div className="space-y-4">
              <TextArea
                id="rm-winrate"
                label="Win Rate & ARR Evaluation"
                value={rmWinrateArr}
                onChange={setRmWinrateArr}
                placeholder="How did your win rate and average risk-reward look this week?"
              />
              <TextArea
                id="rm-stance"
                label="Market Stance Accuracy"
                value={rmStanceAccuracy}
                onChange={setRmStanceAccuracy}
                placeholder="Was your market stance call accurate? Bullish/Bearish/Neutral alignment..."
              />
              <TextArea
                id="rm-rpt"
                label="RPT Consistency"
                value={rmRptConsistency}
                onChange={setRmRptConsistency}
                placeholder="Did you follow the RPT rules consistently?"
              />
              <ToggleSwitch
                checked={rmOrViolated}
                onChange={setRmOrViolated}
                label="OR Matrix Violated?"
                accentColor="red"
              />
              <TextArea
                id="rm-slippage"
                label="Slippage Issues"
                value={rmSlippage}
                onChange={setRmSlippage}
                placeholder="Any slippage issues on entries or exits?"
              />
              <TextArea
                id="rm-streak"
                label="Streak Handling"
                value={rmStreak}
                onChange={setRmStreak}
                placeholder="How did you handle winning/losing streaks?"
              />
            </div>
          </FormSection>

          {/* Section 4: Technical Review */}
          <FormSection title="Technical Review" sectionNumber={4}>
            <div className="space-y-4">
              <TextArea
                id="tech-random"
                label="Random / Unplanned Trades?"
                value={techRandom}
                onChange={setTechRandom}
                placeholder="Did you take any trades that weren't in your watchlist / plan?"
              />
              <TextArea
                id="tech-poor"
                label="Poor Setups Taken?"
                value={techPoorSetups}
                onChange={setTechPoorSetups}
                placeholder="Any low-quality setups you entered? Why?"
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextArea
                  id="tech-entry"
                  label="Entry Timing Quality"
                  value={techEntryTiming}
                  onChange={setTechEntryTiming}
                  placeholder="Rate your entry timing..."
                  rows={2}
                />
                <TextArea
                  id="tech-sl"
                  label="SL Placement Quality"
                  value={techSlPlacement}
                  onChange={setTechSlPlacement}
                  placeholder="Were SLs placed correctly?"
                  rows={2}
                />
              </div>
              <TextArea
                id="tech-exit"
                label="Exit Framework Followed?"
                value={techExitFramework}
                onChange={setTechExitFramework}
                placeholder="Did you follow the extension-based exit framework?"
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <TextArea
                  id="tech-extension"
                  label="Extension Judgment"
                  value={techExtension}
                  onChange={setTechExtension}
                  placeholder="NE/GE/EE judgment accuracy..."
                  rows={2}
                />
                <TextArea
                  id="tech-earnings"
                  label="Earnings Handling"
                  value={techEarnings}
                  onChange={setTechEarnings}
                  placeholder="How did you handle earnings events?"
                  rows={2}
                />
              </div>
            </div>
          </FormSection>

          {/* Section 5: Routine Adherence */}
          <FormSection
            title="Routine Adherence"
            sectionNumber={5}
            borderColor="border-emerald-200"
          >
            <div className="mb-4 flex items-center gap-3 px-4 py-3 rounded-lg bg-emerald-50 border border-emerald-200">
              <span className="text-sm text-emerald-700">
                Routine Score:{" "}
                <span className="font-bold font-mono">{routineScore}/4</span>
              </span>
              <div className="flex gap-1 ml-auto">
                {[0, 1, 2, 3].map((idx) => (
                  <div
                    key={idx}
                    className={`w-3 h-3 rounded-full ${
                      idx < routineScore ? "bg-emerald-500" : "bg-slate-200"
                    }`}
                  />
                ))}
              </div>
            </div>
            <div className="space-y-1 divide-y divide-slate-100">
              <ToggleSwitch
                checked={routineScans}
                onChange={setRoutineScans}
                label="Ran daily scans"
                accentColor="emerald"
              />
              <ToggleSwitch
                checked={routineWatchlist}
                onChange={setRoutineWatchlist}
                label="Updated watchlist"
                accentColor="emerald"
              />
              <ToggleSwitch
                checked={routineSetupTracker}
                onChange={setRoutineSetupTracker}
                label="Updated setup tracker"
                accentColor="emerald"
              />
              <ToggleSwitch
                checked={routineScreenTime}
                onChange={setRoutineScreenTime}
                label="Minimised screen time"
                accentColor="emerald"
              />
            </div>
            <div className="mt-4">
              <TextArea
                id="routine-historical"
                label="Historical Analysis Notes"
                value={routineHistorical}
                onChange={setRoutineHistorical}
                placeholder="Any historical analysis or pattern study done this week?"
              />
            </div>
          </FormSection>

          {/* Section 6: Psychology */}
          <FormSection title="Psychology" sectionNumber={6}>
            <div className="space-y-4">
              <ToggleSwitch
                checked={psychAffirmations}
                onChange={setPsychAffirmations}
                label="Affirmations read daily?"
                accentColor="emerald"
              />
              <Separator />
              <TextArea
                id="psych-impulsive"
                label="Impulsive Actions"
                value={psychImpulsive}
                onChange={setPsychImpulsive}
                placeholder="Any impulsive trades or decisions? What triggered them?"
              />
              <TextArea
                id="psych-fear-greed"
                label="Fear / Greed Influence"
                value={psychFearGreed}
                onChange={setPsychFearGreed}
                placeholder="How did fear or greed affect your decisions?"
              />
              <ToggleSwitch
                checked={psychSocialTrading}
                onChange={setPsychSocialTrading}
                label="Social / tip-based trading influence?"
                accentColor="red"
              />
              <Separator />
              <div className="space-y-1.5">
                <Label htmlFor="psych-stress" className="text-sm text-slate-500">
                  Stress Level
                </Label>
                <div className="flex gap-2">
                  {(["LOW", "MEDIUM", "HIGH"] as const).map((level) => {
                    const isActive = psychStress === level;
                    const colorMap = {
                      LOW: isActive
                        ? "bg-emerald-100 text-emerald-700 border-emerald-300"
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
                      MEDIUM: isActive
                        ? "bg-amber-100 text-amber-700 border-amber-300"
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
                      HIGH: isActive
                        ? "bg-red-100 text-red-700 border-red-300"
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
                    };
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setPsychStress(level)}
                        className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${colorMap[level]}`}
                      >
                        {level}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </FormSection>

          {/* Section 7: Summary */}
          <FormSection title="Summary" sectionNumber={7}>
            <div className="space-y-4">
              <TextArea
                id="excelled-at"
                label="Excelled at this week"
                value={excelledAt}
                onChange={setExcelledAt}
                placeholder="What went well? What are you proud of?"
                rows={4}
              />
              <TextArea
                id="poor-at"
                label="Poor at this week"
                value={poorAt}
                onChange={setPoorAt}
                placeholder="What needs improvement? What mistakes were made?"
                rows={4}
              />
              <TextArea
                id="key-learnings"
                label="Key Learnings"
                value={keyLearnings}
                onChange={setKeyLearnings}
                placeholder="What are the most important lessons from this week?"
                rows={4}
              />
            </div>
          </FormSection>

          {/* Save Button */}
          <div className="flex items-center justify-between pt-2 pb-4">
            <p className="text-xs text-slate-400">
              Week: {weekStart} to {weekEnd}
              {hasGraveMistake && (
                <span className="ml-3 text-red-600 font-semibold">
                  * Grave mistakes flagged
                </span>
              )}
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting || !weekStart || !weekEnd}
                className="bg-teal-600 text-white hover:bg-teal-700 px-8"
              >
                {submitting ? "Saving..." : "Save Journal Entry"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Journal History                                                   */}
      {/* ---------------------------------------------------------------- */}
      {loading ? (
        <JournalTableSkeleton />
      ) : error ? (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">Error Loading Journals</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600 mb-3">{error}</p>
            <Button
              onClick={fetchJournals}
              variant="outline"
              className="text-sm"
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : journals.length === 0 && !showForm ? (
        <EmptyState onNew={() => setShowForm(true)} />
      ) : journals.length > 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-800">
              Journal History
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {journals.length} {journals.length === 1 ? "entry" : "entries"} -- click a row to expand
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Week
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Account Start
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Account End
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Return %
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Trades
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Win Rate
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    ARR
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Key Learnings
                  </th>
                </tr>
              </thead>
              <tbody>
                {journals.map((journal) => {
                  const isExpanded = expandedId === journal.id;
                  return (
                    <JournalRow
                      key={journal.id}
                      journal={journal}
                      isExpanded={isExpanded}
                      onToggle={() =>
                        setExpandedId(isExpanded ? null : journal.id)
                      }
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Journal Table Row (extracted to avoid React key warning with fragments)
// ---------------------------------------------------------------------------

function JournalRow({
  journal,
  isExpanded,
  onToggle,
}: {
  journal: Journal;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className={`border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer ${
          isExpanded ? "bg-slate-50" : ""
        }`}
      >
        <td className="px-4 py-3 text-sm font-medium text-slate-800 whitespace-nowrap">
          {formatWeekRange(journal.week_start, journal.week_end)}
        </td>
        <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
          {journal.account_value_start !== null
            ? formatINR(journal.account_value_start)
            : "--"}
        </td>
        <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
          {journal.account_value_end !== null
            ? formatINR(journal.account_value_end)
            : "--"}
        </td>
        <td className="px-4 py-3 text-right">
          {journal.weekly_return_pct !== null ? (
            <span
              className={`text-sm font-mono font-semibold ${
                journal.weekly_return_pct >= 0
                  ? "text-emerald-600"
                  : "text-red-600"
              }`}
            >
              {formatPct(journal.weekly_return_pct)}
            </span>
          ) : (
            <span className="text-sm text-slate-400">--</span>
          )}
        </td>
        <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
          {journal.trades_taken ?? "--"}
        </td>
        <td className="px-4 py-3 text-right">
          {journal.win_rate !== null ? (
            <span
              className={`text-sm font-mono font-semibold ${
                journal.win_rate >= 40
                  ? "text-emerald-600"
                  : "text-red-600"
              }`}
            >
              {journal.win_rate.toFixed(1)}%
            </span>
          ) : (
            <span className="text-sm text-slate-400">--</span>
          )}
        </td>
        <td className="px-4 py-3 text-right">
          {journal.arr !== null ? (
            <span
              className={`text-sm font-mono font-semibold ${
                journal.arr >= 0
                  ? "text-emerald-600"
                  : "text-red-600"
              }`}
            >
              {journal.arr.toFixed(2)}
            </span>
          ) : (
            <span className="text-sm text-slate-400">--</span>
          )}
        </td>
        <td className="px-4 py-3 text-sm text-slate-600 max-w-[200px]">
          <span title={journal.key_learnings ?? undefined}>
            {truncate(journal.key_learnings, 50)}
          </span>
        </td>
      </tr>
      {isExpanded && <JournalDetail journal={journal} />}
    </>
  );
}
