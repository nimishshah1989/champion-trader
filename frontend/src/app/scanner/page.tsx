import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ScannerPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Scanner</h1>
        <p className="text-muted-foreground">Run PPC, NPC, and Contraction scans — post-market daily</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>PPC Scan</CardTitle>
            <CardDescription>Positive Pivotal Candle — bullish accumulation signals</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Scanner engine not yet implemented — Phase 4</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>NPC Scan</CardTitle>
            <CardDescription>Negative Pivotal Candle — bearish distribution signals</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Scanner engine not yet implemented — Phase 4</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Contraction Scan</CardTitle>
            <CardDescription>Base contraction — volatility coiling before breakout</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Scanner engine not yet implemented — Phase 4</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
