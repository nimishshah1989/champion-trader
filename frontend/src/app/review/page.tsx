"use client";

import { useState } from "react";
import { WeeklyReviewTab } from "./components/weekly-review-tab";
import { LearnTab } from "./components/learn-tab";

// ---------------------------------------------------------------------------
// Tab types
// ---------------------------------------------------------------------------

type TabId = "review" | "learn";

const TABS: { id: TabId; label: string }[] = [
  { id: "review", label: "Weekly Review" },
  { id: "learn", label: "Learn" },
];

// ---------------------------------------------------------------------------
// Review Page — Tabbed layout merging Journal + Methodology
// ---------------------------------------------------------------------------

export default function ReviewPage() {
  const [activeTab, setActiveTab] = useState<TabId>("review");

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">
            Review & Learn
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Weekly self-review and Champion Trader methodology guide
          </p>
        </div>
      </div>

      {/* Tab Pills */}
      <div className="flex items-center gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={
              activeTab === tab.id
                ? "bg-teal-600 text-white rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
                : "bg-white text-slate-600 border border-slate-200 rounded-full px-4 py-1.5 text-sm font-medium hover:bg-slate-50 transition-colors"
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "review" && <WeeklyReviewTab />}
      {activeTab === "learn" && <LearnTab />}
    </div>
  );
}
