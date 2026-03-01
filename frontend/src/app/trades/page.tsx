import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function TradesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Trade Log</h1>
        <p className="text-muted-foreground">Full trade history with P&amp;L and R-multiples</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Trades</CardDescription>
            <CardTitle className="text-2xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Win Rate</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>ARR</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total P&amp;L</CardDescription>
            <CardTitle className="text-2xl">—</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Trades</CardTitle>
          <CardDescription>No trades yet. Enter your first trade after taking a position.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Trade management with partial exits — Phase 3</p>
        </CardContent>
      </Card>
    </div>
  );
}
