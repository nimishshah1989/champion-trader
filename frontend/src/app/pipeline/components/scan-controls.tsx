"use client";

import { InfoTooltip } from "@/components/info-tooltip";
import {
  type ScanType,
  SCAN_TYPE_OPTIONS,
  getTodayISO,
} from "./pipeline-types";

// ---------------------------------------------------------------------------
// Scan Controls — type selector, date picker, run button, summary bar
// ---------------------------------------------------------------------------

interface ScanControlsProps {
  scanType: ScanType;
  onScanTypeChange: (t: ScanType) => void;
  scanDate: string;
  onDateChange: (d: string) => void;
  onRunScan: () => void;
  isScanning: boolean;
  /** Summary counts — only displayed when results exist */
  resultCounts: { total: number; ppc: number; npc: number; contraction: number } | null;
  scanDateLabel: string | null;
}

const INPUT_CLASS =
  "bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";

export function ScanControls({
  scanType,
  onScanTypeChange,
  scanDate,
  onDateChange,
  onRunScan,
  isScanning,
  resultCounts,
  scanDateLabel,
}: ScanControlsProps) {
  return (
    <div className="space-y-3">
      {/* Control row */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-end gap-4">
          {/* Scan Type */}
          <div>
            <label className="text-xs text-slate-500 mb-1 block font-medium">
              Scan Type
            </label>
            <select
              className={INPUT_CLASS}
              value={scanType}
              onChange={(e) => onScanTypeChange(e.target.value as ScanType)}
              disabled={isScanning}
            >
              {SCAN_TYPE_OPTIONS.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label}
                </option>
              ))}
            </select>
          </div>

          {/* Scan Date */}
          <div>
            <label className="text-xs text-slate-500 mb-1 block font-medium">
              Scan Date
            </label>
            <input
              type="date"
              className={INPUT_CLASS}
              value={scanDate}
              onChange={(e) => onDateChange(e.target.value)}
              disabled={isScanning}
              max={getTodayISO()}
            />
          </div>

          {/* Run Scan */}
          <button
            onClick={onRunScan}
            disabled={isScanning}
            className="bg-teal-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
          >
            {isScanning ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Scanning...
              </>
            ) : (
              "Run Scan"
            )}
          </button>

          {/* Scan type tooltips (contextual help) */}
          <div className="flex items-center gap-3 ml-auto text-xs text-slate-400">
            <InfoTooltip termKey="PPC" showFullTerm />
            <InfoTooltip termKey="NPC" showFullTerm />
            <InfoTooltip termKey="CONTRACTION" showFullTerm />
          </div>
        </div>

        {/* Scanning progress */}
        {isScanning && (
          <div className="mt-3 bg-teal-50 border border-teal-200 rounded-lg px-4 py-3">
            <p className="text-sm text-teal-700 font-medium">
              Scanning ~500 NIFTY stocks... this takes 1-2 minutes
            </p>
            <p className="text-xs text-teal-600 mt-1">
              Downloading price data in batches, then running Positive Pivotal Candle / Negative Pivotal Candle / Base Contraction detection.
            </p>
          </div>
        )}
      </div>

      {/* Summary bar */}
      {resultCounts && resultCounts.total > 0 && !isScanning && (
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex flex-wrap items-center gap-4">
          <div className="text-xs text-slate-500">
            <span className="font-medium text-slate-700">
              {resultCounts.total} signals found
            </span>
            {scanDateLabel && (
              <span className="ml-2">for {scanDateLabel}</span>
            )}
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <span className="text-xs font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />
              Positive Pivotal Candle: {resultCounts.ppc}
            </span>
            <span className="text-xs font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />
              Negative Pivotal Candle: {resultCounts.npc}
            </span>
            <span className="text-xs font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />
              Base Contraction: {resultCounts.contraction}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
