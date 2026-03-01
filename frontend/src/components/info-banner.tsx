"use client";

import { useState, useEffect } from "react";

interface InfoBannerProps {
  title: string;
  storageKey: string;
  children: React.ReactNode;
}

export function InfoBanner({ title, storageKey, children }: InfoBannerProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(`info-banner-${storageKey}`);
    if (stored === "collapsed") {
      setIsOpen(false);
    }
    setMounted(true);
  }, [storageKey]);

  function toggle() {
    const next = !isOpen;
    setIsOpen(next);
    localStorage.setItem(
      `info-banner-${storageKey}`,
      next ? "expanded" : "collapsed",
    );
  }

  // Avoid hydration mismatch — render nothing until mounted
  if (!mounted) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-teal-500 overflow-hidden">
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50/50 transition-colors"
      >
        <span className="text-xs font-semibold text-teal-700">{title}</span>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <div className="px-4 pb-3 text-xs text-slate-600 leading-relaxed space-y-1">
          {children}
        </div>
      )}
    </div>
  );
}

export function Term({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <p>
      <span className="font-semibold text-slate-700">{label}</span>
      {" — "}
      {children}
    </p>
  );
}
