import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StockCardProps {
  symbol: string;
  stage?: string;
  bucket?: string;
  triggerLevel?: number;
  trpPct?: number;
  baseDays?: number;
  wucTypes?: string[];
  notes?: string;
}

export function StockCard({
  symbol,
  stage,
  bucket,
  triggerLevel,
  trpPct,
  baseDays,
  wucTypes,
  notes,
}: StockCardProps) {
  const bucketColor =
    bucket === "READY"
      ? "text-green-600"
      : bucket === "NEAR"
        ? "text-amber-600"
        : "text-blue-600";

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{symbol}</CardTitle>
          {bucket && <Badge variant="outline" className={bucketColor}>{bucket}</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {stage && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Stage</span>
            <span>{stage}</span>
          </div>
        )}
        {baseDays !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Base Days</span>
            <span>{baseDays}</span>
          </div>
        )}
        {trpPct !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">TRP%</span>
            <span>{trpPct}%</span>
          </div>
        )}
        {triggerLevel !== undefined && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Trigger Level</span>
            <span className="font-mono font-semibold">{triggerLevel}</span>
          </div>
        )}
        {wucTypes && wucTypes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {wucTypes.map((wuc) => (
              <Badge key={wuc} variant="secondary" className="text-xs">
                {wuc}
              </Badge>
            ))}
          </div>
        )}
        {notes && <p className="text-xs text-muted-foreground">{notes}</p>}
      </CardContent>
    </Card>
  );
}
