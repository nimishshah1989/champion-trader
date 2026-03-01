import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function JournalPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Weekly Journal</h1>
        <p className="text-muted-foreground">Champion Journal — structured weekly self-review</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Journal Sections</CardTitle>
          <CardDescription>Each weekly review covers 5 areas</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li><strong>1. Grave Mistakes</strong> — 5 binary checks (any yes = serious review)</li>
            <li><strong>2. Risk Management</strong> — win rate, ARR, stance accuracy, OR matrix</li>
            <li><strong>3. Technical</strong> — setup quality, entry timing, SL placement, exits</li>
            <li><strong>4. Routine</strong> — scans, watchlist updates, screen time discipline</li>
            <li><strong>5. Psychology</strong> — impulsive actions, fear/greed, stress level</li>
          </ul>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">Full journal form — Phase 3</p>
    </div>
  );
}
