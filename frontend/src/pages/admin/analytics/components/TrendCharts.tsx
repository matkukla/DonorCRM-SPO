import { LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAdminTeamTrends } from "@/hooks/useInsights"

const trendConfig = {
  decisions_logged: { label: "Decisions", color: "hsl(var(--chart-1))" },
  donations_received: { label: "Donations", color: "hsl(var(--chart-2))" },
  stage_progressions: { label: "Stage Changes", color: "hsl(var(--chart-3))" },
} satisfies ChartConfig

export function TrendCharts() {
  const { data, isLoading } = useAdminTeamTrends()

  if (isLoading) return <ChartSkeleton />
  if (!data?.trends.length) return <EmptyChart />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Metrics (12 Weeks)</CardTitle>
        <CardDescription>Decisions, donations, and stage progressions</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={trendConfig} className="min-h-[300px] w-full">
          <LineChart data={data.trends}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="week_label"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
              tick={{ fontSize: 12 }}
            />
            <YAxis tickLine={false} axisLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line
              dataKey="decisions_logged"
              stroke="var(--color-decisions_logged)"
              strokeWidth={2}
              dot={{ r: 4 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="donations_received"
              stroke="var(--color-donations_received)"
              strokeWidth={2}
              dot={{ r: 4 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="stage_progressions"
              stroke="var(--color-stage_progressions)"
              strokeWidth={2}
              dot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Metrics (12 Weeks)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="min-h-[300px] bg-muted rounded animate-pulse" />
      </CardContent>
    </Card>
  )
}

function EmptyChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Metrics (12 Weeks)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="min-h-[300px] flex items-center justify-center">
          <p className="text-muted-foreground">No trend data available</p>
        </div>
      </CardContent>
    </Card>
  )
}
