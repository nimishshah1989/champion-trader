"use client";

import { getTodayISO } from "./pipeline-types";

// ---------------------------------------------------------------------------
// Scan Controls — date picker, run button, v2 setup summary bar
// ---------------------------------------------------------------------------

interface ScanControlsProps {
  scanDate: string;
  onDateChange: (d: string) => void;
  onRunScan: () => void;
  isScanning: boolean;
  /** v2 setup counts by stage — only displayed when results exist */
  resultCounts: { total: number; s1b: number; s2: number } | null;
  scanDateLabel: string | null;
}

const INPUT_CLASS =
  "bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";

export function ScanControls({
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
              "Run v2 Setup Scan"
            )}
          </button>

          <p className="text-xs text-slate-400 ml-auto max-w-sm">
            Validated v2 scan: Stage-2 uptrend + volatility contraction + avg TRP &ge; 2,
            buying the break of the 5-day high. The &ge;2x breakout-volume check fires live
            at entry.
          </p>
        </div>

        {/* Scanning progress */}
        {isScanning && (
          <div className="mt-3 bg-teal-50 border border-teal-200 rounded-lg px-4 py-3">
            <p className="text-sm text-teal-700 font-medium">
              Running the validated v2 setup scan across the liquid NSE universe...
            </p>
            <p className="text-xs text-teal-600 mt-1">
              Reading the Kite-adjusted bar store and evaluating each symbol through the
              parity-proven runtime. READY setups auto-populate the board below.
            </p>
          </div>
        )}
      </div>

      {/* Summary bar */}
      {resultCounts && resultCounts.total > 0 && !isScanning && (
        <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex flex-wrap items-center gap-4">
          <div className="text-xs text-slate-500">
            <span className="font-medium text-slate-700">
              {resultCounts.total} v2 setup{resultCounts.total === 1 ? "" : "s"} found
            </span>
            {scanDateLabel && <span className="ml-2">for {scanDateLabel}</span>}
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <span className="text-xs font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-teal-500 mr-1" />
              Stage S1B: {resultCounts.s1b}
            </span>
            <span className="text-xs font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />
              Stage S2: {resultCounts.s2}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
