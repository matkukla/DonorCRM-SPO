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
import { useWeeklyEngagement } from "@/hooks/useAdminAnalytics"
import { CHART_COLORS } from "@/lib/chart-palette"

interface WeeklyEngagementTileProps {
  weeks?: number
}

export function WeeklyEngagementTile({ weeks = 12 }: WeeklyEngagementTileProps) {
  const { data, isLoading, error } = useWeeklyEngagement({ weeks })

  if (isLoading) {
    return (
      <Card data-testid="weekly-engagement-tile" data-state="loading">
        <CardHeader>
          <CardTitle>Weekly Engagement</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card data-testid="weekly-engagement-tile" data-state="error">
        <CardHeader>
          <CardTitle>Weekly Engagement</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
            <p className="text-destructive text-sm">Failed to load weekly engagement.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const hasAnyActivity = data.weeks.some(
    (w) => w.active_missionaries > 0 || w.on_pace_missionaries > 0,
  )

  return (
    <Card className="flex flex-col" data-testid="weekly-engagement-tile" data-state="ready">
      <CardHeader>
        <CardTitle>Weekly Engagement</CardTitle>
        <CardDescription>
          Active missionaries and on-pace count over the last {weeks} weeks.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        {!hasAnyActivity ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <p className="text-muted-foreground">No engagement data for this window.</p>
          </div>
        ) : (
          <ChartContainer
            config={{}}
            className="flex-1 w-full min-h-[320px] aspect-auto"
          >
            <ComposedChart data={data.weeks} margin={{ top: 20, right: 20, left: 0, bottom: 16 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="week_label"
                  tick={{ fontSize: 11 }}
                  stroke="hsl(var(--muted-foreground))"
                  interval={0}
                  minTickGap={0}
                  angle={-35}
                  textAnchor="end"
                  height={48}
                />
                <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
                <Tooltip
                  content={({ payload, label }) => {
                    if (!payload?.length) return null
                    return (
                      <div className="bg-background border rounded-lg p-2 shadow-lg text-sm">
                        <p className="font-medium mb-1">Week of {label}</p>
                        {payload.map((item, idx) => (
                          <p key={item.name ?? idx} className="text-muted-foreground">
                            <span
                              className="inline-block w-2 h-2 rounded-full mr-2 align-middle"
                              style={{ backgroundColor: item.color }}
                            />
                            {item.name}: <span className="font-medium text-foreground">{item.value}</span>
                          </p>
                        ))}
                      </div>
                    )
                  }}
                />
                <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: 12 }} />
                <Bar
                  dataKey="active_missionaries"
                  name="Active"
                  fill={CHART_COLORS[0]}
                  radius={[2, 2, 0, 0]}
                />
                <Line
                  type="monotone"
                  dataKey="on_pace_missionaries"
                  name="On pace"
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
