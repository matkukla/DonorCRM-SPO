import { useState } from "react"
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { useMonthlyGifts } from "@/hooks/useDashboard"
import { BarChart3, LineChart as LineChartIcon } from "lucide-react"
import { cn } from "@/lib/utils"

const chartConfig = {
  total: { label: "Gifts", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig

type ChartType = "bar" | "line"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function MonthlyGiftsCard({ userId }: { userId?: string }) {
  const { data, isLoading } = useMonthlyGifts(12, userId)
  const [chartType, setChartType] = useState<ChartType>(() => {
    const stored = localStorage.getItem("dashboard-chart-type")
    return stored === "line" ? "line" : "bar"
  })

  const toggleChartType = (type: ChartType) => {
    setChartType(type)
    localStorage.setItem("dashboard-chart-type", type)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="p-4 pl-7">
          <div className="flex items-center justify-between">
            <CardTitle>Monthly Gifts</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-4 pl-7 pt-0 pb-4">
          <div className="min-h-[220px] bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (!data || data.months.every((m) => m.total === 0)) {
    return (
      <Card>
        <CardHeader className="p-4 pl-7">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Monthly Gifts</CardTitle>
              <CardDescription>Donations received by month</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 pl-7 pt-0 pb-4">
          <p className="text-muted-foreground text-sm py-8 text-center">
            No donations recorded yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="p-4 pl-7">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Monthly Gifts</CardTitle>
            <CardDescription>Last 12 months of donations received</CardDescription>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => toggleChartType("bar")}
              className={cn(
                "p-1.5 rounded-md transition-colors",
                chartType === "bar"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
              aria-label="Bar chart"
            >
              <BarChart3 className="h-4 w-4" />
            </button>
            <button
              onClick={() => toggleChartType("line")}
              className={cn(
                "p-1.5 rounded-md transition-colors",
                chartType === "line"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
              aria-label="Line chart"
            >
              <LineChartIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pl-7 pt-0 pb-4">
        <div key={chartType} className="animate-in fade-in duration-300">
          <ChartContainer config={chartConfig} className="min-h-[220px] w-full">
            {chartType === "bar" ? (
              <BarChart data={data.months}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="short_label"
                  tickLine={false}
                  tickMargin={10}
                  axisLine={false}
                />
                <YAxis
                  tickFormatter={(v) => `$${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                  tickLine={false}
                  axisLine={false}
                />
                <ChartTooltip
                  isAnimationActive={false}
                  position={{ y: 10 }}
                  content={
                    <ChartTooltipContent
                      labelKey="total"
                      formatter={(value) => formatCurrency(value as number)}
                    />
                  }
                  cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }}
                />
                {data.monthly_goal > 0 && (
                  <ReferenceLine
                    y={data.monthly_goal}
                    stroke="hsl(var(--destructive))"
                    strokeDasharray="3 3"
                    label={{
                      value: `Goal ${formatCurrency(data.monthly_goal)}`,
                      position: "insideTopRight",
                      fill: "hsl(var(--destructive))",
                      fontSize: 11,
                    }}
                  />
                )}
                <Bar
                  dataKey="total"
                  fill="var(--color-total)"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            ) : (
              <LineChart data={data.months}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="short_label"
                  tickLine={false}
                  tickMargin={10}
                  axisLine={false}
                />
                <YAxis
                  tickFormatter={(v) => `$${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                  tickLine={false}
                  axisLine={false}
                />
                <ChartTooltip
                  isAnimationActive={false}
                  position={{ y: 10 }}
                  content={
                    <ChartTooltipContent
                      labelKey="total"
                      formatter={(value) => formatCurrency(value as number)}
                    />
                  }
                  cursor={{ stroke: "hsl(var(--muted-foreground))", strokeWidth: 1 }}
                />
                {data.monthly_goal > 0 && (
                  <ReferenceLine
                    y={data.monthly_goal}
                    stroke="hsl(var(--destructive))"
                    strokeDasharray="3 3"
                    label={{
                      value: `Goal ${formatCurrency(data.monthly_goal)}`,
                      position: "insideTopRight",
                      fill: "hsl(var(--destructive))",
                      fontSize: 11,
                    }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="total"
                  stroke="var(--color-total)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            )}
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  )
}
