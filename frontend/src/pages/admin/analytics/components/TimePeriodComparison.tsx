import { useMemo } from "react"
import { format, differenceInDays, subDays } from "date-fns"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAdminDashboardOverview } from "@/hooks/useInsights"
import type { DashboardOverviewResponse } from "@/api/insights"

interface TimePeriodComparisonProps {
  dateParams?: {
    date_from?: string
    date_to?: string
  }
  /**
   * Already-fetched overview data for the current period.
   * When a user has selected a date range, the parent dashboard already fetched
   * this same data — passing it in avoids a duplicate network request.
   */
  currentOverview?: DashboardOverviewResponse
}

export function TimePeriodComparison({ dateParams, currentOverview }: TimePeriodComparisonProps) {
  // Calculate prior period
  const { currentDateParams, priorDateParams, currentLabel, priorLabel } = useMemo(() => {
    if (!dateParams?.date_from || !dateParams?.date_to) {
      // Default: current month vs last month
      const now = new Date()
      const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1)
      const currentMonthEnd = now
      const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0)

      return {
        currentDateParams: {
          date_from: format(currentMonthStart, 'yyyy-MM-dd'),
          date_to: format(currentMonthEnd, 'yyyy-MM-dd'),
        },
        priorDateParams: {
          date_from: format(lastMonthStart, 'yyyy-MM-dd'),
          date_to: format(lastMonthEnd, 'yyyy-MM-dd'),
        },
        currentLabel: format(currentMonthStart, 'MMM d') + ' - ' + format(currentMonthEnd, 'MMM d'),
        priorLabel: format(lastMonthStart, 'MMM d') + ' - ' + format(lastMonthEnd, 'MMM d'),
      }
    }

    // Parse dates
    const fromParts = dateParams.date_from.split('-')
    const toParts = dateParams.date_to.split('-')
    const from = new Date(parseInt(fromParts[0]), parseInt(fromParts[1]) - 1, parseInt(fromParts[2]))
    const to = new Date(parseInt(toParts[0]), parseInt(toParts[1]) - 1, parseInt(toParts[2]))

    const daysDiff = differenceInDays(to, from)
    const priorFrom = subDays(from, daysDiff + 1)
    const priorTo = subDays(to, daysDiff + 1)

    return {
      currentDateParams: dateParams,
      priorDateParams: {
        date_from: format(priorFrom, 'yyyy-MM-dd'),
        date_to: format(priorTo, 'yyyy-MM-dd'),
      },
      currentLabel: format(from, 'MMM d') + ' - ' + format(to, 'MMM d'),
      priorLabel: format(priorFrom, 'MMM d') + ' - ' + format(priorTo, 'MMM d'),
    }
  }, [dateParams])

  // When a date range is selected, currentDateParams matches the parent's dateParams
  // and the parent already fetched this data. Skip the duplicate request in that case.
  const canReuseParentOverview = Boolean(
    currentOverview &&
      dateParams?.date_from === currentDateParams.date_from &&
      dateParams?.date_to === currentDateParams.date_to,
  )

  const { data: fetchedCurrentData, isLoading: currentLoading } = useAdminDashboardOverview(
    currentDateParams,
    { enabled: !canReuseParentOverview },
  )
  const { data: priorData, isLoading: priorLoading } = useAdminDashboardOverview(priorDateParams)

  const currentData = canReuseParentOverview ? currentOverview : fetchedCurrentData
  const isLoading = (!canReuseParentOverview && currentLoading) || priorLoading

  const metrics = useMemo(() => {
    if (!currentData || !priorData) return []

    const calculateChange = (current: number, previous: number) => {
      if (previous === 0 && current > 0) return 100
      if (previous === 0 && current === 0) return 0
      return ((current - previous) / previous) * 100
    }

    return [
      {
        label: 'Total Contacts',
        current: currentData.total_contacts,
        previous: priorData.total_contacts,
        change: calculateChange(currentData.total_contacts, priorData.total_contacts),
      },
      {
        label: 'Conversion Rate',
        current: currentData.conversion_rate,
        previous: priorData.conversion_rate,
        change: calculateChange(currentData.conversion_rate, priorData.conversion_rate),
        suffix: '%',
      },
      {
        label: 'Stalled Contacts',
        current: currentData.stalled_contacts,
        previous: priorData.stalled_contacts,
        change: calculateChange(currentData.stalled_contacts, priorData.stalled_contacts),
      },
      {
        label: 'Donations (12m)',
        current: currentData.donations_12m.total_amount,
        previous: priorData.donations_12m.total_amount,
        change: calculateChange(currentData.donations_12m.total_amount, priorData.donations_12m.total_amount),
        isCurrency: true,
      },
    ]
  }, [currentData, priorData])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Time Period Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 bg-muted rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (!currentData || !priorData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Time Period Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Select a date range to compare periods</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{currentLabel} vs {priorLabel}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {metrics.map((metric) => {
            const isPositive = metric.change > 0
            const isNegative = metric.change < 0
            const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus

            return (
              <div key={metric.label} className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">{metric.label}</p>
                <p className="text-2xl font-bold">
                  {metric.isCurrency
                    ? metric.current.toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD',
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })
                    : metric.current.toLocaleString()}
                  {metric.suffix || ''}
                </p>
                <div className="flex items-center gap-1 text-xs">
                  <span className="text-muted-foreground">
                    vs {metric.isCurrency
                      ? metric.previous.toLocaleString('en-US', {
                          style: 'currency',
                          currency: 'USD',
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      : metric.previous.toLocaleString()}
                    {metric.suffix || ''}
                  </span>
                  <TrendIcon
                    className={`w-3 h-3 ${
                      isPositive
                        ? 'text-green-600 dark:text-green-400'
                        : isNegative
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-muted-foreground'
                    }`}
                  />
                  <span
                    className={`font-medium ${
                      isPositive
                        ? 'text-green-600 dark:text-green-400'
                        : isNegative
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {isPositive ? '+' : ''}{metric.change.toFixed(1)}%
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
