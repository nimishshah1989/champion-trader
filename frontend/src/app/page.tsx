import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Daily command centre — Champion Trader routine</p>
      </div>

      {/* Morning block */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Morning Check</h2>
          <Badge variant="outline">15 min</Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Open Positions</CardDescription>
              <CardTitle className="text-3xl">0</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">No positions yet</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Open Risk</CardDescription>
              <CardTitle className="text-3xl">0%</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Max allowed: 10%</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Market Stance</CardDescription>
              <CardTitle className="text-3xl">—</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">No stance logged today</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Market close block */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Market Close</h2>
          <Badge variant="outline">30 min</Badge>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>READY Stocks</CardTitle>
            <CardDescription>Stocks with trigger levels set — ready to enter</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">No READY stocks in watchlist. Add stocks via the Watchlist page.</p>
          </CardContent>
        </Card>
      </div>

      {/* Post-market block */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Post-Market Analysis</h2>
          <Badge variant="outline">1 hour</Badge>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Daily Scans</CardTitle>
            <CardDescription>Run PPC, NPC, and Contraction scans after market close</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Scanner not yet implemented — Phase 4</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
