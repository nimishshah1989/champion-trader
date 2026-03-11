"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { InfoTooltip } from "@/components/info-tooltip";
import { getJournals, type Journal } from "@/lib/api";
import { NewJournalForm } from "./new-journal-form";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(value: number | null): string {
  if (value === null || value === undefined) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatWeekRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${s.toLocaleDateString("en-IN", opts)} - ${e.toLocaleDateString("en-IN", opts)}, ${e.getFullYear()}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function JournalSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, idx) => (
        <div key={idx} className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-4">
            <Skeleton className="h-4 w-32 bg-slate-100" />
            <Skeleton className="h-4 w-16 bg-slate-100" />
            <Skeleton className="h-4 w-16 bg-slate-100" />
            <Skeleton className="h-4 w-20 bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

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
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        No journal entries yet
      </h3>
      <p className="text-sm text-slate-500 mb-4 max-w-md mx-auto">
        Start your weekly self-review. Track grave mistakes, performance
        metrics, and key learnings.
      </p>
      <Button onClick={onNew} className="bg-teal-600 text-white hover:bg-teal-700">
        + New Journal Entry
      </Button>
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
      <p className="text-sm text-red-600 mb-3">{message}</p>
      <Button variant="outline" onClick={onRetry} className="text-sm">
        Retry
      </Button>
    </div>
  );
}

function JournalCard({ journal }: { journal: Journal }) {
  const returnColor =
    (journal.weekly_return_pct ?? 0) >= 0 ? "text-emerald-600" : "text-red-600";
  const winRateColor =
    (journal.win_rate ?? 0) >= 40 ? "text-emerald-600" : "text-red-600";

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <p className="text-sm font-semibold text-slate-800">
          {formatWeekRange(journal.week_start, journal.week_end)}
        </p>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-400">Return</span>
          <span className={`text-sm font-mono font-semibold ${returnColor}`}>
            {formatPct(journal.weekly_return_pct)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-400">
            <InfoTooltip termKey="WIN_RATE">Win Rate</InfoTooltip>
          </span>
          <span className={`text-sm font-mono font-semibold ${winRateColor}`}>
            {journal.win_rate !== null
              ? `${journal.win_rate.toFixed(1)}%`
              : "--"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-400">
            <InfoTooltip termKey="ARR">ARR</InfoTooltip>
          </span>
          <span className="text-sm font-mono font-semibold text-slate-700">
            {journal.arr !== null ? journal.arr.toFixed(2) : "--"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-400">Trades</span>
          <span className="text-sm font-mono font-semibold text-slate-700">
            {journal.trades_taken ?? "--"}
          </span>
        </div>
      </div>
      {/* Summary row */}
      {(journal.excelled_at || journal.poor_at || journal.key_learnings) && (
        <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-3">
          {journal.excelled_at && (
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Excelled At
              </p>
              <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">
                {journal.excelled_at}
              </p>
            </div>
          )}
          {journal.poor_at && (
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Poor At
              </p>
              <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">
                {journal.poor_at}
              </p>
            </div>
          )}
          {journal.key_learnings && (
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Key Learnings
              </p>
              <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">
                {journal.key_learnings}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Tab Component
// ---------------------------------------------------------------------------

export function WeeklyReviewTab() {
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const fetchJournals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJournals();
      setJournals(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load journals";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJournals();
  }, [fetchJournals]);

  function handleSaved() {
    setShowForm(false);
    fetchJournals();
  }

  if (showForm) {
    return (
      <NewJournalForm
        onSaved={handleSaved}
        onCancel={() => setShowForm(false)}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Action bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {loading
            ? "Loading..."
            : `${journals.length} journal ${journals.length === 1 ? "entry" : "entries"}`}
        </p>
        <Button
          onClick={() => setShowForm(true)}
          className="bg-teal-600 text-white hover:bg-teal-700"
        >
          + New Journal Entry
        </Button>
      </div>

      <Separator />

      {/* States */}
      {loading && <JournalSkeleton />}
      {!loading && error && (
        <ErrorState message={error} onRetry={fetchJournals} />
      )}
      {!loading && !error && journals.length === 0 && (
        <EmptyState onNew={() => setShowForm(true)} />
      )}
      {!loading && !error && journals.length > 0 && (
        <div className="space-y-3">
          {journals.map((j) => (
            <JournalCard key={j.id} journal={j} />
          ))}
        </div>
      )}
    </div>
  );
}
