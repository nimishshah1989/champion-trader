"use client";

import { useState } from "react";
import { TradesTab } from "./components/trades-tab";
import { PerformanceTab } from "./components/performance-tab";

// ---------------------------------------------------------------------------
// Tab type
// ---------------------------------------------------------------------------

type TradesPageTab = "trades" | "performance";

const TABS: { key: TradesPageTab; label: string }[] = [
  { key: "trades", label: "Trades" },
  { key: "performance", label: "Performance" },
];

// ---------------------------------------------------------------------------
// Trades Page — Tab Wrapper
// ---------------------------------------------------------------------------

export default function TradesPage() {
  const [activeTab, setActiveTab] = useState<TradesPageTab>("trades");

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
            Trade Log
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Full trade history with P&L tracking and R-multiples
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-5 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-teal-600 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "trades" && <TradesTab />}
      {activeTab === "performance" && <PerformanceTab />}
    </div>
  );
}
