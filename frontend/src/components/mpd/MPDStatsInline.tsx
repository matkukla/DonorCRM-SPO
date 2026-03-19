import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatMPDCurrency, formatMonthsRemaining } from "@/api/mpd"

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
        <CardHeader className="p-4 pl-7 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Monthly Average
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pl-7 pt-0 pb-4">
          <div className="text-2xl font-bold">
            {formatMPDCurrency(monthlyAverage ?? null)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-4 pl-7 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            MPD Cap
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pl-7 pt-0 pb-4">
          <div className="text-2xl font-bold">
            {formatMPDCurrency(currentMpdCap ?? null)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-4 pl-7 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Roll Forward Balance
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pl-7 pt-0 pb-4">
          <div className="text-2xl font-bold">
            {formatMPDCurrency(latestRollForwardBalance ?? null)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-4 pl-7 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Months Remaining
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pl-7 pt-0 pb-4">
          <div className="text-2xl font-bold">
            {formatMonthsRemaining(monthsRemainingRf)}
          </div>
        </CardContent>
      </Card>
    </>
  )
}
