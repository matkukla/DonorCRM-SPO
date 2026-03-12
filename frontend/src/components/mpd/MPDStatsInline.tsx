import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatMPDCurrency } from "@/api/mpd"

interface MPDStatsInlineProps {
  monthlyAverage: string | null | undefined
  currentMpdCap: string | null | undefined
  latestRollForwardBalance: string | null | undefined
  monthsRemainingRf: string | undefined
}

/**
 * Renders 4 Card items showing MPD financial data.
 * Used as Fragment children — parent provides the grid wrapper.
 */
export function MPDStatsInline({
  monthlyAverage,
  currentMpdCap,
  latestRollForwardBalance,
  monthsRemainingRf,
}: MPDStatsInlineProps) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Monthly Average
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatMPDCurrency(monthlyAverage ?? null)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            MPD Cap
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatMPDCurrency(currentMpdCap ?? null)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Roll Forward Balance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {formatMPDCurrency(latestRollForwardBalance ?? null)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Months Remaining
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {monthsRemainingRf || "--"}
          </div>
        </CardContent>
      </Card>
    </>
  )
}
