import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function MarketStancePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Market Stance</h1>
        <p className="text-muted-foreground">Daily sector strength assessment — drives RPT% and position limits</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Current Stance</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">No stance logged today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Suggested RPT%</CardDescription>
            <CardTitle className="text-2xl">0.50%</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Default — adjusts with stance</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Max Positions</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Weak: 3-4 | Moderate: 5-6 | Strong: 8-10</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stance History</CardTitle>
          <CardDescription>Daily log with strong/weak sector tracking</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Market stance tracking — Phase 2</p>
        </CardContent>
      </Card>
    </div>
  );
}
