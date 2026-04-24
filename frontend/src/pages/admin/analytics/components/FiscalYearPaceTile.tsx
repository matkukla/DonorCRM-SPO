import { ArrowDownIcon, ArrowUpIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useFiscalYearPace } from "@/hooks/useAdminAnalytics"
import { clampPercentage, formatCents } from "@/lib/format"
import { formatLocalDate } from "@/lib/utils"

export function FiscalYearPaceTile() {
  const { data, isLoading, error } = useFiscalYearPace()

  if (isLoading) {
    return (
      <Card data-testid="fy-pace-tile" data-state="loading">
        <CardHeader>
          <CardTitle>Fiscal Year Pace</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card data-testid="fy-pace-tile" data-state="error">
        <CardHeader>
          <CardTitle>Fiscal Year Pace</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
            <p className="text-destructive text-sm">Failed to load fiscal year pace.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const hasGoal = data.annual_goal_cents > 0
  const progressValue = hasGoal
    ? clampPercentage((data.raised_cents / data.annual_goal_cents) * 100, 0, 100)
    : 0
  const paceDisplay = clampPercentage(data.pace_percentage, 0, 150)
  const onPace = paceDisplay >= 100

  const yoy = data.yoy_delta_percentage
  const importedCaption = data.last_import_at
    ? `Data as of ${formatLocalDate(data.last_import_at, "long")}`
    : "Updated daily from Raiser's Edge"

  return (
    <Card data-testid="fy-pace-tile" data-state="ready">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div>
          <CardTitle>Fiscal Year Pace</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            {formatLocalDate(data.fy_start, "short")} – {formatLocalDate(data.fy_end, "short")}
          </p>
        </div>
        <Badge variant={onPace ? "default" : "secondary"} data-testid="fy-pace-badge">
          {paceDisplay.toFixed(0)}% of pace
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Raised
            </p>
            <p
              className="text-3xl font-bold tracking-tight"
              data-testid="fy-pace-raised"
            >
              {formatCents(data.raised_cents, { whole: true })}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Annual Goal
            </p>
            <p className="text-xl font-semibold">
              {hasGoal ? formatCents(data.annual_goal_cents, { whole: true }) : "No goal set"}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Expected to date
            </p>
            <p className="text-xl font-semibold">
              {formatCents(data.expected_by_today_cents, { whole: true })}
            </p>
          </div>
        </div>

        <Progress value={progressValue} className="h-3" />

        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div data-testid="fy-pace-yoy">
            {yoy === null ? (
              <Badge variant="outline">No prior year data</Badge>
            ) : (
              <span
                className={`inline-flex items-center gap-1 text-sm font-medium ${
                  yoy >= 0 ? "text-emerald-600" : "text-destructive"
                }`}
              >
                {yoy >= 0 ? (
                  <ArrowUpIcon className="h-4 w-4" aria-hidden />
                ) : (
                  <ArrowDownIcon className="h-4 w-4" aria-hidden />
                )}
                {yoy >= 0 ? "+" : ""}
                {yoy.toFixed(1)}% vs. last year
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground" data-testid="fy-pace-import-caption">
            {importedCaption}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
