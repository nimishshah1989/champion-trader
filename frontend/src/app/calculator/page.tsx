"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

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

function calculatePosition(
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
  const [accountValue, setAccountValue] = useState<number>(500000);
  const [rptPct, setRptPct] = useState<number>(0.5);
  const [symbol, setSymbol] = useState<string>("");
  const [entryPrice, setEntryPrice] = useState<number>(0);
  const [trpPct, setTrpPct] = useState<number>(0);

  const result = calculatePosition(accountValue, rptPct, entryPrice, trpPct);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Position Calculator</h1>
        <p className="text-muted-foreground">Calculate position size, SL, and extension targets</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Input form */}
        <Card>
          <CardHeader>
            <CardTitle>Inputs</CardTitle>
            <CardDescription>Results update in real-time as you type</CardDescription>
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
            <div className="space-y-2">
              <Label htmlFor="account-value">Account Value</Label>
              <Input
                id="account-value"
                type="number"
                value={accountValue || ""}
                onChange={(e) => setAccountValue(Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rpt-pct">RPT % (Risk Per Trade)</Label>
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
              <Label htmlFor="trp-pct">TRP % (True Range Percentage)</Label>
              <Input
                id="trp-pct"
                type="number"
                step="0.01"
                value={trpPct || ""}
                onChange={(e) => setTrpPct(Number(e.target.value))}
              />
            </div>
          </CardContent>
        </Card>

        {/* Output */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
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
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Position Size</span>
                    <span className="font-mono text-xl font-bold">{result.position_size} shares</span>
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
            <CardHeader>
              <CardTitle>Stop Loss</CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SL Price</span>
                    <span className="font-mono font-semibold text-red-600">{formatINR(result.sl_price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SL Amount</span>
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
            <CardHeader>
              <CardTitle>Extension Targets</CardTitle>
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
                    <span className="text-muted-foreground">Normal Extension (4x TRP)</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">Exit 20%</Badge>
                      <span className="font-mono font-semibold text-green-600">{formatINR(result.target_ne)}</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Great Extension (8x TRP)</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">Exit 40%</Badge>
                      <span className="font-mono font-semibold text-green-600">{formatINR(result.target_ge)}</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Extreme Extension (12x TRP)</span>
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
    </div>
  );
}
