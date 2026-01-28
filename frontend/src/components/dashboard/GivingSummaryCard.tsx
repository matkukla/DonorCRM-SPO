import { PieChart, Pie, Cell } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { useGivingSummary } from "@/hooks/useDashboard"

const chartConfig = {
  given: { label: "Given", color: "hsl(var(--chart-1))" },
  remaining: { label: "Remaining", color: "hsl(var(--muted))" },
} satisfies ChartConfig

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function GivingSummaryCard() {
  const { data, isLoading } = useGivingSummary()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Given and Expecting</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-6 items-center">
            <div className="h-[180px] w-[180px] bg-muted rounded-full animate-pulse" />
            <div className="flex-1 space-y-3 w-full">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-6 bg-muted rounded animate-pulse" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.annual_goal === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Given and Expecting</CardTitle>
          <CardDescription>Track progress toward your annual goal</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm py-8 text-center">
            Set a monthly goal in settings to track giving progress.
          </p>
        </CardContent>
      </Card>
    )
  }

  const percentage = Math.round(data.percentage)
  const remaining = Math.max(0, data.annual_goal - data.given)

  const donutData = [
    { name: "Given", value: data.given },
    { name: "Remaining", value: remaining },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Given and Expecting</CardTitle>
        <CardDescription>
          Annual Goal {formatCurrency(data.annual_goal)} ({formatCurrency(data.monthly_goal)} monthly)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col md:flex-row gap-6 items-center">
          {/* Donut Chart */}
          <div className="relative">
            <ChartContainer config={chartConfig} className="h-[180px] w-[180px]">
              <PieChart>
                <Pie
                  data={donutData}
                  dataKey="value"
                  innerRadius={60}
                  outerRadius={80}
                  startAngle={90}
                  endAngle={-270}
                  strokeWidth={0}
                >
                  <Cell fill="hsl(var(--chart-1))" />
                  <Cell fill="hsl(var(--muted))" />
                </Pie>
              </PieChart>
            </ChartContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold">{percentage}%</span>
              <span className="text-xs text-muted-foreground">{formatCurrency(data.given)}</span>
            </div>
          </div>

          {/* Summary Table */}
          <div className="flex-1 space-y-3 w-full">
            <div className="flex justify-between items-center py-1.5 border-b">
              <span className="text-sm text-muted-foreground">Given</span>
              <span className="text-sm font-semibold text-green-600">
                {formatCurrency(data.given)}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b">
              <span className="text-sm text-muted-foreground">Expecting</span>
              <span className="text-sm font-medium">
                {formatCurrency(data.expecting)}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b">
              <span className="text-sm text-muted-foreground">Total</span>
              <span className="text-sm font-bold">
                {formatCurrency(data.total)}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-sm text-muted-foreground">Recurring Pledges</span>
              <span className="text-sm font-medium">
                {formatCurrency(data.recurring_pledges_annual)}/yr
                <span className="text-muted-foreground ml-1">({data.active_pledge_count} active)</span>
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-xs text-muted-foreground mt-4">
          Updated today &middot; {data.year} calendar year
        </p>
      </CardContent>
    </Card>
  )
}
