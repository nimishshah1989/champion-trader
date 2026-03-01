"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoBanner, Term } from "@/components/info-banner";

export default function PerformancePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Performance</h1>
        <p className="text-muted-foreground">Expectancy metrics, P&amp;L charts, and R-multiple analysis</p>
      </div>

      <InfoBanner title="Quick Reference — Performance Metrics" storageKey="performance">
        <Term label="Win Rate">Profitable trades / Total closed trades. Target &gt;40%. Being right only 4/10 times is fine if winners are big.</Term>
        <Term label="ARR">Average Risk-Reward. Target &gt;2.0. Measures whether you let winners run and cut losers short.</Term>
        <Term label="Expectancy">Expected R earned per trade. Positive = you have an edge. Formula: (WR x Avg Win) - (LR x Avg Loss).</Term>
        <Term label="R-Multiple">Standard measure of trade performance. 1R = risked amount. A +3R trade returned 3x what was risked.</Term>
        <Term label="Total P&L">Cumulative profit/loss across all closed trades.</Term>
      </InfoBanner>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Win Rate</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Target: &gt;40%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>ARR</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Target: &gt;2.0</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Expectancy / Trade</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">(WR x Avg Win R) - (LR x Avg Loss R)</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total P&amp;L</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">All-time</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Monthly P&amp;L</CardTitle>
            <CardDescription>Bar chart — each bar is one month</CardDescription>
          </CardHeader>
          <CardContent className="h-48 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">Charts — Phase 5</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>R-Multiple Distribution</CardTitle>
            <CardDescription>Histogram of R-multiples across all trades</CardDescription>
          </CardHeader>
          <CardContent className="h-48 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">Charts — Phase 5</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
