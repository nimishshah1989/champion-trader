"use client";

import Link from "next/link";
import {
  SectionHeading,
  WhatIsThisTool,
  DailyRoutine,
  PagesExplained,
  BehindTheScenes,
} from "./components/guide-sections";
import {
  JargonBuster,
  FAQ,
  GettingStarted,
} from "./components/guide-reference";

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function IntelligenceGuidePage() {
  return (
    <div className="space-y-8">
      {/* Breadcrumb + Header */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <Link
            href="/intelligence"
            className="text-xs text-teal-600 hover:text-teal-700 font-medium"
          >
            Intelligence
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">How It Works</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">
          How This Tool Works
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Everything you need to know — explained in plain language, no jargon
        </p>
      </div>

      {/* 1. The Big Picture */}
      <WhatIsThisTool />

      {/* 2. Your Daily Routine */}
      <DailyRoutine />

      {/* 3. Each Page Explained */}
      <div className="space-y-3">
        <SectionHeading>What Each Page Does</SectionHeading>
        <PagesExplained />
      </div>

      {/* 4. Behind the Scenes */}
      <div className="space-y-3">
        <SectionHeading>Behind the Scenes</SectionHeading>
        <BehindTheScenes />
      </div>

      {/* 5. Jargon Buster */}
      <JargonBuster />

      {/* 6. FAQ */}
      <FAQ />

      {/* 7. Getting Started */}
      <GettingStarted />

      {/* Footer link back to dashboard */}
      <div className="flex justify-center pb-4">
        <Link
          href="/intelligence"
          className="text-sm text-teal-600 hover:text-teal-700 font-medium"
        >
          ← Back to Intelligence Dashboard
        </Link>
      </div>
    </div>
  );
}
