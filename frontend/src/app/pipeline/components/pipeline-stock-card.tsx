"use client";

import Link from "next/link";
import { InfoTooltip } from "@/components/info-tooltip";
import {
  type Bucket,
  type PipelineCard,
  BUCKET_META,
  BUCKET_ORDER,
  STAGE_COLORS,
  formatINR,
} from "./pipeline-types";

// ---------------------------------------------------------------------------
// Pipeline Stock Card — individual card displayed in the kanban columns
// ---------------------------------------------------------------------------

interface PipelineStockCardProps {
  card: PipelineCard;
  onMove: (symbol: string, watchlistId: number | null, newBucket: Bucket) => void;
  onRemove: (symbol: string, watchlistId: number | null) => void;
  isUpdating: boolean;
}

function StageBadge({ stage }: { stage: string | null }) {
  if (!stage) return null;
  const color = STAGE_COLORS[stage] || "bg-slate-100 text-slate-500";
  return (
    <span className={`${color} rounded-full px-2 py-0.5 text-[11px] font-semibold`}>
      {stage}
    </span>
  );
}

function ScanTypeBadge({ scanType }: { scanType: string | null }) {
  if (!scanType) return null;
  const colorMap: Record<string, string> = {
    PPC: "bg-emerald-100 text-emerald-700",
    NPC: "bg-red-100 text-red-700",
    CONTRACTION: "bg-blue-100 text-blue-700",
  };
  const color = colorMap[scanType] || "bg-slate-100 text-slate-600";
  const labelMap: Record<string, string> = {
    PPC: "PPC",
    NPC: "NPC",
    CONTRACTION: "CTR",
  };
  return (
    <span className={`${color} rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase`}>
      {labelMap[scanType] || scanType}
    </span>
  );
}

export function PipelineStockCard({
  card,
  onMove,
  onRemove,
  isUpdating,
}: PipelineStockCardProps) {
  const movableBuckets = BUCKET_ORDER.filter((b) => b !== card.bucket);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-colors">
      {/* Header: Symbol + badges */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-slate-800 tracking-wide">
          {card.symbol}
        </span>
        <div className="flex items-center gap-1.5">
          <ScanTypeBadge scanType={card.scanType} />
          <StageBadge stage={card.stage} />
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs mb-3">
        {/* Close price */}
        {card.closePrice !== null && (
          <div>
            <span className="text-slate-400">Close</span>
            <span className="ml-1 font-mono font-semibold text-slate-700">
              {formatINR(card.closePrice)}
            </span>
          </div>
        )}

        {/* True Range Percentage */}
        {card.trp !== null && (
          <div className="flex items-center gap-0.5">
            <span className="text-slate-400">
              True Range Percentage <InfoTooltip termKey="TRP" />
            </span>
            <span
              className={`ml-1 font-mono font-semibold ${
                card.trp >= 2.0 ? "text-emerald-600" : "text-slate-700"
              }`}
            >
              {card.trp.toFixed(2)}%
            </span>
          </div>
        )}

        {/* Volume Ratio */}
        {card.volumeRatio !== null && (
          <div className="flex items-center gap-0.5">
            <span className="text-slate-400">
              Volume Ratio <InfoTooltip termKey="VOL_RATIO" />
            </span>
            <span
              className={`ml-1 font-mono font-semibold ${
                card.volumeRatio >= 1.5 ? "text-emerald-600" : "text-slate-700"
              }`}
            >
              {card.volumeRatio.toFixed(2)}x
            </span>
          </div>
        )}

        {/* Base Days */}
        {card.baseDays !== null && card.baseDays > 0 && (
          <div>
            <span className="text-slate-400">Base Days</span>
            <span
              className={`ml-1 font-mono font-semibold ${
                card.baseDays >= 20 ? "text-emerald-600" : "text-slate-700"
              }`}
            >
              {card.baseDays}d
            </span>
          </div>
        )}

        {/* Trigger Level */}
        {card.triggerLevel !== null && (
          <div className="flex items-center gap-0.5">
            <span className="text-slate-400">
              Trigger <InfoTooltip termKey="TRIGGER" />
            </span>
            <span className="ml-1 font-mono font-semibold text-emerald-600">
              {formatINR(card.triggerLevel)}
            </span>
          </div>
        )}
      </div>

      {/* Position sizing section */}
      {(card.positionSize !== null || card.halfQty !== null) && (
        <div className="bg-slate-50 rounded-lg px-3 py-2 mb-3">
          <div className="flex items-center gap-4 text-xs">
            {card.positionSize !== null && (
              <div className="flex items-center gap-0.5">
                <span className="text-slate-400">
                  Position Size <InfoTooltip termKey="POSITION_SIZE" />
                </span>
                <span className="ml-1 font-mono font-semibold text-slate-800">
                  {card.positionSize}
                </span>
              </div>
            )}
            {card.halfQty !== null && (
              <div className="flex items-center gap-0.5">
                <span className="text-slate-400">
                  Half Qty <InfoTooltip termKey="HALF_QTY" />
                </span>
                <span className="ml-1 font-mono font-semibold text-teal-600">
                  {card.halfQty}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Notes */}
      {card.notes && (
        <p className="text-xs text-slate-500 mb-2 line-clamp-2 italic">
          {card.notes}
        </p>
      )}

      {/* Added date (only for watchlist-persisted items) */}
      {card.addedDate && (
        <p className="text-[10px] text-slate-400 mb-2">
          Added{" "}
          {new Date(card.addedDate).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </p>
      )}

      {/* Not-yet-saved indicator */}
      {card.watchlistId === null && (
        <p className="text-[10px] text-amber-500 font-medium mb-2">
          From scan results (not yet saved to watchlist)
        </p>
      )}

      {/* Action row */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100 flex-wrap">
        {/* Move buttons */}
        {movableBuckets.map((b) => {
          const meta = BUCKET_META[b];
          return (
            <button
              key={b}
              disabled={isUpdating}
              onClick={() => onMove(card.symbol, card.watchlistId, b)}
              className={`text-[11px] font-medium px-2.5 py-1 rounded border transition-colors disabled:opacity-50 ${meta.headerBg} ${meta.borderColor} ${meta.color} hover:opacity-80`}
            >
              {b}
            </button>
          );
        })}

        {/* Calculator link */}
        <Link
          href={`/calculator?symbol=${encodeURIComponent(card.symbol)}${
            card.triggerLevel ? `&entry_price=${card.triggerLevel}` : ""
          }${card.trp ? `&trp_pct=${card.trp}` : ""}`}
          className="text-[11px] font-medium px-2.5 py-1 rounded border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors ml-auto"
        >
          Calculate
        </Link>

        {/* Remove */}
        <button
          disabled={isUpdating}
          onClick={() => onRemove(card.symbol, card.watchlistId)}
          className="text-[11px] font-medium px-2.5 py-1 rounded border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 transition-colors disabled:opacity-50"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
