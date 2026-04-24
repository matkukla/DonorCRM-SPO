import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer } from "@/components/ui/chart"
import { useFiscalYearDonations } from "@/hooks/useAdminAnalytics"
import { CHART_COLORS } from "@/lib/chart-palette"
import { formatCents } from "@/lib/format"

export function FiscalYearDonationsTile() {
  const { data, isLoading, error } = useFiscalYearDonations()

  if (isLoading) {
    return (
      <Card data-testid="fy-donations-tile" data-state="loading">
        <CardHeader>
          <CardTitle>Fiscal Year Donations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card data-testid="fy-donations-tile" data-state="error">
        <CardHeader>
          <CardTitle>Fiscal Year Donations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
            <p className="text-destructive text-sm">Failed to load donation totals.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const hasAnyData = data.current_fy_total_cents > 0 || data.prior_fy_total_cents > 0

  // Recharts prefers dollar values; compute once for axis readability.
  const chartData = data.months.map((m) => ({
    short_label: m.short_label,
    // `null` current_cents hides the bar for future months automatically.
    current_dollars: m.current_cents === null ? null : m.current_cents / 100,
    prior_dollars: m.prior_cents / 100,
    is_future: m.is_future,
  }))

  return (
    <Card data-testid="fy-donations-tile" data-state="ready">
      <CardHeader>
        <CardTitle>Fiscal Year Donations</CardTitle>
        <CardDescription className="flex flex-wrap gap-x-6 gap-y-1">
          <span>
            Current FY total:{" "}
            <span className="font-medium text-foreground">
              {formatCents(data.current_fy_total_cents, { whole: true })}
            </span>
          </span>
          <span>
            Prior FY total:{" "}
            <span className="font-medium text-foreground">
              {formatCents(data.prior_fy_total_cents, { whole: true })}
            </span>
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!hasAnyData ? (
          <div className="py-12 text-center">
            <p className="text-muted-foreground">No donation data yet.</p>
          </div>
        ) : (
          <ChartContainer config={{}} className="h-[320px] w-full">
            <ComposedChart data={chartData} margin={{ top: 16, right: 24, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="short_label"
                  tick={{ fontSize: 12 }}
                  stroke="hsl(var(--muted-foreground))"
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  stroke="hsl(var(--muted-foreground))"
                  tickFormatter={(v: number) =>
                    v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${v}`
                  }
                />
                <Tooltip
                  content={({ payload, label }) => {
                    if (!payload?.length) return null
                    const current = payload.find((p) => p.dataKey === "current_dollars")
                    const prior = payload.find((p) => p.dataKey === "prior_dollars")
                    return (
                      <div className="bg-background border rounded-lg p-2 shadow-lg text-sm">
                        <p className="font-medium mb-1">{label}</p>
                        {current && current.value !== null && current.value !== undefined ? (
                          <p className="text-muted-foreground">
                            Current FY:{" "}
                            <span className="font-medium text-foreground">
                              {formatCents(Math.round((current.value as number) * 100), {
                                whole: true,
                              })}
                            </span>
                          </p>
                        ) : null}
                        {prior ? (
                          <p className="text-muted-foreground">
                            Prior FY:{" "}
                            <span className="font-medium text-foreground">
                              {formatCents(Math.round((prior.value as number) * 100), {
                                whole: true,
                              })}
                            </span>
                          </p>
                        ) : null}
                      </div>
                    )
                  }}
                />
                <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: 12 }} />
                <Bar
                  dataKey="current_dollars"
                  name="Current FY"
                  fill={CHART_COLORS[0]}
                  radius={[2, 2, 0, 0]}
                />
                <Line
                  type="monotone"
                  dataKey="prior_dollars"
                  name="Prior FY"
                  stroke={CHART_COLORS[2]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
            </ComposedChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
