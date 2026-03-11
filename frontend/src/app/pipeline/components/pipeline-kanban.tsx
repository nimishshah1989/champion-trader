"use client";

import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PipelineStockCard } from "./pipeline-stock-card";
import {
  type Bucket,
  type PipelineCard,
  BUCKET_ORDER,
  BUCKET_META,
} from "./pipeline-types";

// ---------------------------------------------------------------------------
// Pipeline Kanban — 3-column READY | NEAR | AWAY board
// ---------------------------------------------------------------------------

interface PipelineKanbanProps {
  cards: PipelineCard[];
  loading: boolean;
  error: string | null;
  onMove: (symbol: string, watchlistId: number | null, newBucket: Bucket) => void;
  onRemove: (symbol: string, watchlistId: number | null) => void;
  updatingSymbols: Set<string>;
  onRetry: () => void;
  /** Inline add-stock form fields */
  onAddStock: (data: AddStockFormData) => void;
}

export interface AddStockFormData {
  symbol: string;
  bucket: Bucket;
  stage: string;
  triggerLevel: string;
  trpPct: string;
  notes: string;
}

const EMPTY_FORM: AddStockFormData = {
  symbol: "",
  bucket: "NEAR",
  stage: "",
  triggerLevel: "",
  trpPct: "",
  notes: "",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ColumnSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
          <Skeleton className="h-5 w-24 bg-slate-100" />
          <Skeleton className="h-4 w-32 bg-slate-100" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-12 bg-slate-100 rounded-full" />
            <Skeleton className="h-5 w-14 bg-slate-100 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full bg-slate-100" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-7 w-16 bg-slate-100 rounded" />
            <Skeleton className="h-7 w-16 bg-slate-100 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyColumn({ bucket }: { bucket: Bucket }) {
  const meta = BUCKET_META[bucket];
  const iconMap: Record<string, string> = {
    target: "\uD83C\uDFAF",
    eye: "\uD83D\uDC41",
    radar: "\uD83D\uDCE1",
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
      <div className="text-3xl mb-2 text-slate-300">
        {iconMap[meta.emptyIcon] || "\u2014"}
      </div>
      <p className="text-sm text-slate-400">{meta.emptyText}</p>
    </div>
  );
}

function InlineAddForm({
  onAdd,
  onCancel,
}: {
  onAdd: (data: AddStockFormData) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<AddStockFormData>(EMPTY_FORM);

  function updateField<K extends keyof AddStockFormData>(key: K, value: AddStockFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.symbol.trim()) return;
    onAdd(form);
    setForm(EMPTY_FORM);
  }

  const inputClass =
    "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";
  const labelClass = "text-xs text-slate-500 mb-1 block font-medium";

  return (
    <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-teal-500 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-800">Add Stock Manually</h3>
        <button
          onClick={onCancel}
          className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
        >
          Cancel
        </button>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3 items-end">
          <div>
            <label className={labelClass}>Symbol *</label>
            <input
              type="text"
              placeholder="RELIANCE"
              className={inputClass}
              value={form.symbol}
              onChange={(e) => updateField("symbol", e.target.value.toUpperCase())}
              autoFocus
            />
          </div>
          <div>
            <label className={labelClass}>Bucket</label>
            <select
              className={inputClass}
              value={form.bucket}
              onChange={(e) => updateField("bucket", e.target.value as Bucket)}
            >
              <option value="AWAY">AWAY</option>
              <option value="NEAR">NEAR</option>
              <option value="READY">READY</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Stage</label>
            <select
              className={inputClass}
              value={form.stage}
              onChange={(e) => updateField("stage", e.target.value)}
            >
              <option value="">Select</option>
              <option value="S1">S1</option>
              <option value="S1B">S1B</option>
              <option value="S2">S2</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Trigger Level</label>
            <input
              type="number"
              step="0.05"
              placeholder="Price"
              className={inputClass}
              value={form.triggerLevel}
              onChange={(e) => updateField("triggerLevel", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>True Range Percentage</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 3.18"
              className={inputClass}
              value={form.trpPct}
              onChange={(e) => updateField("trpPct", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>Notes</label>
            <input
              type="text"
              placeholder="Observations..."
              className={inputClass}
              value={form.notes}
              onChange={(e) => updateField("notes", e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={!form.symbol.trim()}
            className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 whitespace-nowrap"
          >
            + Add
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Kanban Board
// ---------------------------------------------------------------------------

export function PipelineKanban({
  cards,
  loading,
  error,
  onMove,
  onRemove,
  updatingSymbols,
  onRetry,
  onAddStock,
}: PipelineKanbanProps) {
  const [showAddForm, setShowAddForm] = useState(false);

  // Group cards by bucket
  const buckets: Record<Bucket, PipelineCard[]> = {
    READY: cards.filter((c) => c.bucket === "READY"),
    NEAR: cards.filter((c) => c.bucket === "NEAR"),
    AWAY: cards.filter((c) => c.bucket === "AWAY"),
  };

  return (
    <div className="space-y-4">
      {/* Add stock toggle + inline form */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-800">Pipeline Board</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono tabular-nums">
            {cards.length} stock{cards.length !== 1 ? "s" : ""}
          </span>
          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm flex items-center gap-1"
            >
              <span>+</span> Add Stock
            </button>
          )}
        </div>
      </div>

      {showAddForm && (
        <InlineAddForm
          onAdd={(data) => {
            onAddStock(data);
            setShowAddForm(false);
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">Failed to load pipeline data</p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={onRetry}
            className="bg-red-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Kanban columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {BUCKET_ORDER.map((bucket) => {
          const meta = BUCKET_META[bucket];
          const columnCards = buckets[bucket];

          return (
            <div key={bucket} className="space-y-3">
              {/* Column header */}
              <div
                className={`${meta.headerBg} ${meta.borderColor} border rounded-xl px-4 py-3 flex items-center justify-between`}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${meta.color}`}>
                    {meta.label}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    ({columnCards.length})
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
                  {meta.subtitle}
                </span>
              </div>

              {/* Loading */}
              {loading && <ColumnSkeleton />}

              {/* Empty */}
              {!loading && !error && columnCards.length === 0 && (
                <EmptyColumn bucket={bucket} />
              )}

              {/* Cards */}
              {!loading &&
                !error &&
                columnCards.map((card) => (
                  <PipelineStockCard
                    key={`${card.symbol}-${card.watchlistId ?? "scan"}`}
                    card={card}
                    onMove={onMove}
                    onRemove={onRemove}
                    isUpdating={updatingSymbols.has(card.symbol)}
                  />
                ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
