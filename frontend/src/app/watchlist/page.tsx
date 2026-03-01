"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getWatchlist,
  addToWatchlist,
  updateWatchlistItem,
  removeFromWatchlist,
  type WatchlistItem,
} from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoBanner, Term } from "@/components/info-banner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Bucket = "READY" | "NEAR" | "AWAY";

interface AddFormData {
  symbol: string;
  bucket: Bucket;
  stage: string;
  trigger_level: string;
  planned_sl_pct: string;
  wuc_types: string;
  notes: string;
}

const EMPTY_FORM: AddFormData = {
  symbol: "",
  bucket: "NEAR",
  stage: "",
  trigger_level: "",
  planned_sl_pct: "",
  wuc_types: "",
  notes: "",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const BUCKET_META: Record<
  Bucket,
  { label: string; color: string; headerBg: string; borderColor: string; emptyText: string }
> = {
  READY: {
    label: "READY",
    color: "text-emerald-700",
    headerBg: "bg-emerald-50",
    borderColor: "border-emerald-200",
    emptyText: "No READY stocks. Promote from NEAR when trigger bar forms.",
  },
  NEAR: {
    label: "NEAR",
    color: "text-amber-700",
    headerBg: "bg-amber-50",
    borderColor: "border-amber-200",
    emptyText: "No NEAR stocks. Promote from AWAY as base matures.",
  },
  AWAY: {
    label: "AWAY",
    color: "text-blue-700",
    headerBg: "bg-blue-50",
    borderColor: "border-blue-200",
    emptyText: "No AWAY stocks. Add from scanner results.",
  },
};

const STAGE_COLORS: Record<string, string> = {
  S1: "bg-emerald-100 text-emerald-700",
  S1B: "bg-teal-100 text-teal-700",
  S2: "bg-blue-100 text-blue-700",
};

const BUCKET_ORDER: Bucket[] = ["READY", "NEAR", "AWAY"];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ColumnSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-white rounded-xl border border-slate-200 p-4 space-y-3"
        >
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
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
      <div className="text-3xl mb-2 text-slate-300">
        {bucket === "READY" ? "🎯" : bucket === "NEAR" ? "👁" : "📡"}
      </div>
      <p className="text-sm text-slate-400">{meta.emptyText}</p>
    </div>
  );
}

function WucBadges({ wucTypes }: { wucTypes: string | null }) {
  if (!wucTypes) return null;
  const types = wucTypes
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  if (types.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {types.map((t) => (
        <span
          key={t}
          className="bg-slate-100 text-slate-600 border border-slate-200 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide"
        >
          {t}
        </span>
      ))}
    </div>
  );
}

function StageBadge({ stage }: { stage: string | null }) {
  if (!stage) return null;
  const color = STAGE_COLORS[stage] || "bg-slate-100 text-slate-600";
  return (
    <span
      className={`${color} rounded-full px-2 py-0.5 text-[11px] font-semibold`}
    >
      {stage}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Stock Card
// ---------------------------------------------------------------------------

function StockCard({
  item,
  onMove,
  onRemove,
  isUpdating,
}: {
  item: WatchlistItem;
  onMove: (id: number, bucket: Bucket) => void;
  onRemove: (id: number) => void;
  isUpdating: boolean;
}) {
  const currentBucket = item.bucket as Bucket;
  const movableBuckets = BUCKET_ORDER.filter((b) => b !== currentBucket);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-colors">
      {/* Header row: Symbol + Stage */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-slate-800 tracking-wide">
          {item.symbol}
        </span>
        <StageBadge stage={item.stage} />
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mb-2">
        {item.base_days !== null && (
          <div>
            <span className="text-slate-400">Base Days</span>
            <span className="ml-1 font-mono font-semibold text-slate-700">
              {item.base_days}
            </span>
          </div>
        )}
        {item.base_quality && (
          <div>
            <span className="text-slate-400">Quality</span>
            <span className="ml-1 font-semibold text-slate-700">
              {item.base_quality}
            </span>
          </div>
        )}
        {item.planned_sl_pct !== null && (
          <div>
            <span className="text-slate-400">TRP%</span>
            <span className="ml-1 font-mono font-semibold text-red-600">
              {item.planned_sl_pct}%
            </span>
          </div>
        )}
        {item.trigger_level !== null && currentBucket === "READY" && (
          <div>
            <span className="text-slate-400">Trigger</span>
            <span className="ml-1 font-mono font-semibold text-emerald-600">
              {formatINR.format(item.trigger_level)}
            </span>
          </div>
        )}
      </div>

      {/* WUC types */}
      <WucBadges wucTypes={item.wuc_types} />

      {/* Notes */}
      {item.notes && (
        <p className="text-xs text-slate-500 mt-2 line-clamp-2 italic">
          {item.notes}
        </p>
      )}

      {/* Added date */}
      <p className="text-[10px] text-slate-400 mt-2">
        Added{" "}
        {new Date(item.added_date).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </p>

      {/* Action row */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
        {/* Move buttons */}
        {movableBuckets.map((b) => {
          const meta = BUCKET_META[b];
          return (
            <button
              key={b}
              disabled={isUpdating}
              onClick={() => onMove(item.id, b)}
              className={`text-[11px] font-medium px-2.5 py-1 rounded border transition-colors disabled:opacity-50 ${meta.headerBg} ${meta.borderColor} ${meta.color} hover:opacity-80`}
            >
              {b}
            </button>
          );
        })}

        {/* Calculator link */}
        <Link
          href={`/calculator?symbol=${encodeURIComponent(item.symbol)}`}
          className="text-[11px] font-medium px-2.5 py-1 rounded border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors ml-auto"
        >
          Calc
        </Link>

        {/* Remove button */}
        <button
          disabled={isUpdating}
          onClick={() => onRemove(item.id)}
          className="text-[11px] font-medium px-2.5 py-1 rounded border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 transition-colors disabled:opacity-50"
        >
          Remove
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add Stock Form
// ---------------------------------------------------------------------------

function AddStockForm({
  onAdd,
  onCancel,
}: {
  onAdd: (data: AddFormData) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<AddFormData>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  function updateField<K extends keyof AddFormData>(key: K, value: AddFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.symbol.trim()) {
      toast.error("Symbol is required");
      return;
    }
    setSubmitting(true);
    onAdd(form);
    setSubmitting(false);
  }

  const inputClass =
    "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";
  const labelClass = "text-xs text-slate-500 mb-1 block font-medium";

  return (
    <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-teal-500 p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-800">Add Stock to Watchlist</h3>
        <button
          onClick={onCancel}
          className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
        >
          Cancel
        </button>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end">
          <div>
            <label className={labelClass}>Symbol *</label>
            <input
              type="text"
              placeholder="e.g. RELIANCE"
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
              value={form.trigger_level}
              onChange={(e) => updateField("trigger_level", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>TRP%</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 7"
              className={inputClass}
              value={form.planned_sl_pct}
              onChange={(e) => updateField("planned_sl_pct", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>WUC Types</label>
            <input
              type="text"
              placeholder="PPC, NPC"
              className={inputClass}
              value={form.wuc_types}
              onChange={(e) => updateField("wuc_types", e.target.value.toUpperCase())}
            />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4 mt-4 items-end">
          <div>
            <label className={labelClass}>Notes</label>
            <input
              type="text"
              placeholder="Setup notes, observations..."
              className={inputClass}
              value={form.notes}
              onChange={(e) => updateField("notes", e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={submitting || !form.symbol.trim()}
            className="bg-teal-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 flex items-center gap-1 justify-center whitespace-nowrap"
          >
            <span>+</span> Add to Watchlist
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<Set<number>>(new Set());

  const fetchWatchlist = useCallback(async () => {
    try {
      setError(null);
      const data = await getWatchlist();
      setItems(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch watchlist";
      setError(message);
      toast.error("Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  // Bucket-grouped items
  const buckets: Record<Bucket, WatchlistItem[]> = {
    READY: items.filter((i) => i.bucket === "READY"),
    NEAR: items.filter((i) => i.bucket === "NEAR"),
    AWAY: items.filter((i) => i.bucket === "AWAY"),
  };

  // --- Handlers ---

  async function handleAdd(formData: AddFormData) {
    try {
      const payload: Parameters<typeof addToWatchlist>[0] = {
        symbol: formData.symbol.trim(),
        bucket: formData.bucket,
      };
      if (formData.stage) payload.stage = formData.stage;
      if (formData.trigger_level) payload.trigger_level = parseFloat(formData.trigger_level);
      if (formData.planned_sl_pct) payload.planned_sl_pct = parseFloat(formData.planned_sl_pct);
      if (formData.wuc_types) payload.wuc_types = formData.wuc_types;
      if (formData.notes) payload.notes = formData.notes;

      await addToWatchlist(payload);
      toast.success(`${payload.symbol} added to ${payload.bucket}`);
      setShowAddForm(false);
      await fetchWatchlist();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to add stock";
      toast.error(message);
    }
  }

  async function handleMove(id: number, newBucket: Bucket) {
    setUpdatingIds((prev) => new Set(prev).add(id));
    try {
      await updateWatchlistItem(id, { bucket: newBucket });
      toast.success(`Moved to ${newBucket}`);
      await fetchWatchlist();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to move stock";
      toast.error(message);
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  async function handleRemove(id: number) {
    const item = items.find((i) => i.id === id);
    setUpdatingIds((prev) => new Set(prev).add(id));
    try {
      await removeFromWatchlist(id);
      toast.success(`${item?.symbol ?? "Stock"} removed`);
      await fetchWatchlist();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to remove stock";
      toast.error(message);
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  // --- Render ---

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
            <span>👁</span> Watchlist
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Kanban view — READY / NEAR / AWAY buckets
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono tabular-nums">
            {items.length} stock{items.length !== 1 ? "s" : ""}
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

      <InfoBanner title="Quick Reference — Watchlist Terms" storageKey="watchlist">
        <Term label="READY">Trigger bar formed, entry imminent. Set price alerts.</Term>
        <Term label="NEAR">Base maturing, 1-2 weeks from potential entry. Watch daily.</Term>
        <Term label="AWAY">Early-stage base forming. Monitor weekly.</Term>
        <Term label="Stage">S1 = Basing, S1B = Late basing (ideal entry zone), S2 = Advancing.</Term>
        <Term label="WUC">Wake-Up Call type: MBB (Moving out of Base Breakout), BA (Breakout Anticipated), EF (Early Flyer).</Term>
        <Term label="TRP%">Stock&apos;s avg daily range as % of price. Used as stop-loss distance.</Term>
        <Term label="Base Days">Consolidation length. Need 20+ bars for a valid base.</Term>
        <Term label="Quality">Base smoothness: SMOOTH (tight, clean) &gt; MIXED &gt; CHOPPY (volatile, unreliable).</Term>
      </InfoBanner>

      {/* Add form (inline, top) */}
      {showAddForm && (
        <AddStockForm
          onAdd={handleAdd}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">Failed to load watchlist</p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchWatchlist();
            }}
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
          const columnItems = buckets[bucket];

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
                    ({columnItems.length})
                  </span>
                </div>
                {bucket === "READY" && (
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
                    Trigger Set
                  </span>
                )}
                {bucket === "NEAR" && (
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
                    Watch Closely
                  </span>
                )}
                {bucket === "AWAY" && (
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
                    Building Base
                  </span>
                )}
              </div>

              {/* Loading skeleton */}
              {loading && <ColumnSkeleton />}

              {/* Empty state */}
              {!loading && !error && columnItems.length === 0 && (
                <EmptyColumn bucket={bucket} />
              )}

              {/* Stock cards */}
              {!loading &&
                !error &&
                columnItems.map((item) => (
                  <StockCard
                    key={item.id}
                    item={item}
                    onMove={handleMove}
                    onRemove={handleRemove}
                    isUpdating={updatingIds.has(item.id)}
                  />
                ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
