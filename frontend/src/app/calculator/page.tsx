"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { calculatePosition as saveToBackend, type PositionCalcResponse } from "@/lib/api";
import { InfoBanner, Term } from "@/components/info-banner";

interface CalcResult {
  rpt_amount: number;
  sl_price: number;
  sl_pct: number;
  sl_amount: number;
  position_value: number;
  position_size: number;
  half_qty: number;
  target_2r: number;
  target_ne: number;
  target_ge: number;
  target_ee: number;
}

function calculateLocally(
  accountValue: number,
  rptPct: number,
  entryPrice: number,
  trpPct: number,
): CalcResult | null {
  if (!accountValue || !rptPct || !entryPrice || !trpPct) return null;

  const rptAmount = accountValue * (rptPct / 100);
  const slPctDecimal = trpPct / 100;
  const slAmount = entryPrice * slPctDecimal;
  const slPrice = entryPrice - slAmount;
  const positionValue = rptAmount / slPctDecimal;
  const positionSize = Math.round(positionValue / entryPrice);
  const halfQty = Math.floor(positionSize / 2);
  const trpValue = slAmount;

  return {
    rpt_amount: Math.round(rptAmount * 100) / 100,
    sl_price: Math.round(slPrice * 100) / 100,
    sl_pct: Math.round(trpPct * 100) / 100,
    sl_amount: Math.round(slAmount * 100) / 100,
    position_value: Math.round(positionValue * 100) / 100,
    position_size: positionSize,
    half_qty: halfQty,
    target_2r: Math.round((entryPrice + 2 * trpValue) * 100) / 100,
    target_ne: Math.round((entryPrice + 4 * trpValue) * 100) / 100,
    target_ge: Math.round((entryPrice + 8 * trpValue) * 100) / 100,
    target_ee: Math.round((entryPrice + 12 * trpValue) * 100) / 100,
  };
}

function formatINR(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

export default function CalculatorPage() {
  return (
    <Suspense>
      <CalculatorContent />
    </Suspense>
  );
}

function CalculatorContent() {
  const searchParams = useSearchParams();
  const [accountValue, setAccountValue] = useState<number>(500000);
  const [rptPct, setRptPct] = useState<number>(0.5);
  const [symbol, setSymbol] = useState<string>("");
  const [entryPrice, setEntryPrice] = useState<number>(0);
  const [trpPct, setTrpPct] = useState<number>(0);
  const [saving, setSaving] = useState(false);

  // Pre-fill symbol from URL query param (e.g. /calculator?symbol=ASTERDM)
  useEffect(() => {
    const urlSymbol = searchParams.get("symbol");
    if (urlSymbol) setSymbol(urlSymbol.toUpperCase());
  }, [searchParams]);
  const [savedCalcs, setSavedCalcs] = useState<Array<{
    symbol: string;
    position_size: number;
    sl_price: number;
    half_qty: number;
  }>>([]);

  const result = calculateLocally(accountValue, rptPct, entryPrice, trpPct);

  async function handleSave() {
    if (!result || !symbol) {
      toast.error("Enter a symbol and all values before saving");
      return;
    }

    setSaving(true);
    try {
      const backendResult = await saveToBackend({
        symbol,
        account_value: accountValue,
        rpt_pct: rptPct,
        entry_price: entryPrice,
        trp_pct: trpPct,
      });

      setSavedCalcs((prev) => [
        {
          symbol,
          position_size: backendResult.position_size,
          sl_price: backendResult.sl_price,
          half_qty: backendResult.half_qty,
        },
        ...prev,
      ]);

      toast.success(`Saved: ${symbol} — ${backendResult.position_size} shares, SL at ${formatINR(backendResult.sl_price)}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save";
      toast.error(message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Position Calculator</h1>
        <p className="text-muted-foreground">Calculate position size, SL, and extension targets — results update in real-time</p>
      </div>

      <InfoBanner title="Quick Reference — Calculator Terms" storageKey="calculator">
        <Term label="Account Value (AV)">Your total trading capital.</Term>
        <Term label="RPT">Risk Per Trade: % of AV risked per trade. Range 0.2%-1.0%, default 0.5%. On a 10L account at 0.5% = max loss per trade.</Term>
        <Term label="TRP%">True Range Percentage: stock&apos;s avg daily range. This becomes your stop-loss distance. Min 2.0% for tradeable stocks.</Term>
        <Term label="SL">Stop Loss = Entry Price - TRP value. Never move SL down.</Term>
        <Term label="Position Size">RPT Amount / (Entry x TRP%), always split 50/50 into two entry tranches.</Term>
        <Term label="Half Qty">Each tranche size. Entry 1 at trigger break, Entry 2 on confirmation.</Term>
        <Term label="Exit targets">2R = 2x risk (book 20%), NE = 4x TRP (book 20%), GE = 8x TRP (book 40%), EE = 12x TRP (book 80%).</Term>
      </InfoBanner>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input form */}
        <Card>
          <CardHeader>
            <CardTitle>Inputs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                placeholder="e.g. ASTERDM"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="account-value">Account Value (AV)</Label>
                <Input
                  id="account-value"
                  type="number"
                  value={accountValue || ""}
                  onChange={(e) => setAccountValue(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rpt-pct">RPT %</Label>
                <Input
                  id="rpt-pct"
                  type="number"
                  step="0.1"
                  min="0.2"
                  max="1.0"
                  value={rptPct || ""}
                  onChange={(e) => setRptPct(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="entry-price">Entry Price</Label>
                <Input
                  id="entry-price"
                  type="number"
                  step="0.05"
                  value={entryPrice || ""}
                  onChange={(e) => setEntryPrice(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="trp-pct">TRP %</Label>
                <Input
                  id="trp-pct"
                  type="number"
                  step="0.01"
                  value={trpPct || ""}
                  onChange={(e) => setTrpPct(Number(e.target.value))}
                />
              </div>
            </div>

            <Separator />

            <Button
              onClick={handleSave}
              disabled={!result || !symbol || saving}
              className="w-full"
            >
              {saving ? "Saving..." : "Save Calculation"}
            </Button>
          </CardContent>
        </Card>

        {/* Output */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Position Sizing</CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">RPT Amount</span>
                    <span className="font-mono font-semibold">{formatINR(result.rpt_amount)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Position Value</span>
                    <span className="font-mono font-semibold">{formatINR(result.position_value)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Position Size</span>
                    <span className="font-mono text-2xl font-bold">{result.position_size} shares</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Half Qty (50/50 entry)</span>
                    <span className="font-mono font-semibold">{result.half_qty} shares</span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Enter all values to see results</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-red-600">Stop Loss</CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SL Price</span>
                    <span className="font-mono text-lg font-bold text-red-600">{formatINR(result.sl_price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SL Amount (per share)</span>
                    <span className="font-mono">{formatINR(result.sl_amount)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SL %</span>
                    <span className="font-mono">{result.sl_pct}%</span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">—</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-green-600">Extension Targets</CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">2R Target</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">Exit 20%</Badge>
                      <span className="font-mono font-semibold text-green-600">{formatINR(result.target_2r)}</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">NE (4x TRP)</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">Exit 20%</Badge>
                      <span className="font-mono font-semibold text-green-600">{formatINR(result.target_ne)}</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">GE (8x TRP)</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">Exit 40%</Badge>
                      <span className="font-mono font-semibold text-green-600">{formatINR(result.target_ge)}</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">EE (12x TRP)</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">Exit 80%</Badge>
                      <span className="font-mono font-semibold text-green-600">{formatINR(result.target_ee)}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">—</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Saved calculations this session */}
      {savedCalcs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Saved This Session</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2">Symbol</th>
                  <th className="py-2">Position Size</th>
                  <th className="py-2">Half Qty</th>
                  <th className="py-2">SL Price</th>
                </tr>
              </thead>
              <tbody>
                {savedCalcs.map((calc, idx) => (
                  <tr key={idx} className="border-b">
                    <td className="py-2 font-medium">{calc.symbol}</td>
                    <td className="py-2 font-mono">{calc.position_size} shares</td>
                    <td className="py-2 font-mono">{calc.half_qty} shares</td>
                    <td className="py-2 font-mono text-red-600">{formatINR(calc.sl_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
