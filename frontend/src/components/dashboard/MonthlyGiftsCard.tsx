import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { useMonthlyGifts } from "@/hooks/useDashboard"

const chartConfig = {
  total: { label: "Gifts", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function MonthlyGiftsCard() {
  const { data, isLoading } = useMonthlyGifts()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Monthly Gifts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="min-h-[220px] bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (!data || data.months.every((m) => m.total === 0)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Monthly Gifts</CardTitle>
          <CardDescription>Donations received by month</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm py-8 text-center">
            No donations recorded yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Monthly Gifts</CardTitle>
        <CardDescription>Last 12 months of donations received</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="min-h-[220px] w-full">
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
        </ChartContainer>

        {/* Footer */}
        <p className="text-xs text-muted-foreground mt-2">
          Updated today
        </p>
      </CardContent>
    </Card>
  )
}
