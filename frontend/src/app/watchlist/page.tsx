import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function WatchlistPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Watchlist</h1>
        <p className="text-muted-foreground">READY / NEAR / AWAY — categorised stock tracking</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-green-600">READY</h2>
          <Card>
            <CardHeader>
              <CardDescription>Contraction + Trigger Bar identified</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">No READY stocks. Add from scanner results.</p>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-amber-600">NEAR</h2>
          <Card>
            <CardHeader>
              <CardDescription>Nearing end of base — watch closely</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">No NEAR stocks.</p>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-blue-600">AWAY</h2>
          <Card>
            <CardHeader>
              <CardDescription>Strong stock, still building base</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">No AWAY stocks.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
