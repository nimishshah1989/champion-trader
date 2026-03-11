"use client";

import { useState } from "react";
import { Settings } from "lucide-react";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useSettings } from "@/contexts/settings-context";
import { formatIndian } from "@/lib/format";

type Stance = "STRONG" | "MODERATE" | "WEAK";
type Exchange = "NSE" | "BSE";

const STANCE_RPT: Record<Stance, number> = { STRONG: 0.5, MODERATE: 0.35, WEAK: 0.2 };
const STANCE_POSITIONS: Record<Stance, number> = { STRONG: 10, MODERATE: 6, WEAK: 4 };
const MAX_OPEN_RISK_PCT = 0.1;

function SectionHeader({ children }: { children: string }) {
  return (
    <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-3">
      {children}
    </p>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-mono font-semibold text-slate-800">{value}</span>
    </div>
  );
}

export function SettingsDrawer({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { settings, updateSettings, effectiveRpt, resetToDefaults } = useSettings();

  const maxOpenRisk = settings.accountValue * MAX_OPEN_RISK_PCT;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="bg-white border-l border-slate-200 overflow-y-auto">
        <SheetHeader className="border-b border-slate-100 pb-4">
          <SheetTitle className="text-lg font-semibold text-slate-800">
            Trading Settings
          </SheetTitle>
          <SheetDescription className="text-sm text-slate-500">
            Configure your account, risk, and market stance.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-6 px-4 py-2">
          {/* --- Section 1: Account --- */}
          <section>
            <SectionHeader>Account</SectionHeader>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="account-value" className="text-sm text-slate-700">
                  Account Value
                </Label>
                <Input
                  id="account-value"
                  type="number"
                  min={0}
                  step={10000}
                  value={settings.accountValue}
                  onChange={(e) =>
                    updateSettings({ accountValue: Math.max(0, Number(e.target.value)) })
                  }
                  className="font-mono"
                />
                <p className="text-xs text-slate-400 font-mono">
                  {formatIndian(settings.accountValue)}
                </p>
              </div>

              <div className="space-y-1.5">
                <Label className="text-sm text-slate-700">Exchange</Label>
                <div className="flex gap-2">
                  {(["NSE", "BSE"] as const).map((ex: Exchange) => (
                    <button
                      key={ex}
                      type="button"
                      onClick={() => updateSettings({ exchange: ex })}
                      className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                        settings.exchange === ex
                          ? "border-teal-600 bg-teal-600 text-white"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* --- Section 2: Risk Management --- */}
          <section>
            <SectionHeader>Risk Management</SectionHeader>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="base-rpt" className="text-sm text-slate-700">
                  Base Risk Per Trade (%)
                </Label>
                <Input
                  id="base-rpt"
                  type="number"
                  min={0.1}
                  max={1.0}
                  step={0.05}
                  value={settings.rptPct}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (!Number.isNaN(val)) {
                      updateSettings({ rptPct: Math.min(1.0, Math.max(0.1, val)) });
                    }
                  }}
                  className="font-mono"
                />
                <p className="text-xs text-slate-400">Adjusted by market stance</p>
              </div>

              <ReadOnlyField label="Effective RPT" value={`${effectiveRpt.toFixed(2)}%`} />
              <ReadOnlyField label="Max Open Risk" value={formatIndian(maxOpenRisk)} />
            </div>
          </section>

          {/* --- Section 3: Market Stance --- */}
          <section>
            <SectionHeader>Market Stance</SectionHeader>

            <div className="space-y-4">
              <div className="flex gap-2">
                {(
                  [
                    { value: "STRONG", label: "Strong", active: "bg-emerald-600 border-emerald-600 text-white", idle: "border-emerald-300 text-emerald-700 hover:bg-emerald-50" },
                    { value: "MODERATE", label: "Moderate", active: "bg-amber-500 border-amber-500 text-white", idle: "border-amber-300 text-amber-700 hover:bg-amber-50" },
                    { value: "WEAK", label: "Weak", active: "bg-red-600 border-red-600 text-white", idle: "border-red-300 text-red-700 hover:bg-red-50" },
                  ] as const
                ).map((s) => {
                  const isActive = settings.currentStance === s.value;
                  return (
                    <button
                      key={s.value}
                      type="button"
                      onClick={() => {
                        const nextStance: Stance | null =
                          settings.currentStance === s.value ? null : s.value;
                        updateSettings({
                          currentStance: nextStance,
                          stanceRptOverride: nextStance ? STANCE_RPT[nextStance] : null,
                        });
                      }}
                      className={`flex-1 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                        isActive ? s.active : s.idle
                      }`}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>

              {settings.currentStance && (
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 space-y-1">
                  <ReadOnlyField
                    label="RPT Override"
                    value={`${STANCE_RPT[settings.currentStance].toFixed(2)}%`}
                  />
                  <ReadOnlyField
                    label="Max Positions"
                    value={String(STANCE_POSITIONS[settings.currentStance])}
                  />
                </div>
              )}

              {!settings.currentStance && (
                <p className="text-xs text-slate-400">
                  Select a stance to auto-derive RPT and max positions.
                </p>
              )}
            </div>
          </section>
        </div>

        {/* --- Footer --- */}
        <div className="mt-auto border-t border-slate-100 px-4 py-4">
          <Button
            variant="link"
            onClick={() => {
              resetToDefaults();
              onOpenChange(false);
            }}
            className="text-sm text-slate-500 hover:text-teal-600 px-0"
          >
            Reset to Defaults
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function SettingsButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        aria-label="Open trading settings"
      >
        <Settings className="w-4 h-4" />
      </button>
      <SettingsDrawer open={open} onOpenChange={setOpen} />
    </>
  );
}
