import { useMemo } from "react"
import { FunnelChart, Funnel, LabelList, Tooltip } from "recharts"
import { ChartContainer } from "@/components/ui/chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAdminConversionFunnel } from "@/hooks/useInsights"

const FUNNEL_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
]

export function ConversionFunnelChart() {
  const { data, isLoading } = useAdminConversionFunnel()

  const chartData = useMemo(() => {
    if (!data?.funnel) return []
    return data.funnel.map((stage, index) => ({
      name: stage.label,
      value: stage.count,
      percentage: stage.percentage,
      fill: FUNNEL_COLORS[index % FUNNEL_COLORS.length],
    }))
  }, [data])

  if (isLoading) return <ChartSkeleton />
  if (!chartData.length) return <EmptyChart />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
        <CardDescription>
          {data?.total_contacts_in_pipeline} contacts in pipeline
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={{}} className="min-h-[400px] w-full">
          <FunnelChart>
            <Tooltip
              content={({ payload }) => {
                if (!payload?.[0]) return null
                const item = payload[0].payload
                return (
                  <div className="bg-background border rounded-lg p-2 shadow-lg">
                    <p className="font-medium">{item.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {item.value} contacts ({item.percentage.toFixed(1)}%)
                    </p>
                  </div>
                )
              }}
            />
            <Funnel
              dataKey="value"
              data={chartData}
              isAnimationActive
            >
              <LabelList
                position="right"
                fill="hsl(var(--foreground))"
                stroke="none"
                dataKey="name"
              />
            </Funnel>
          </FunnelChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="min-h-[400px] bg-muted rounded animate-pulse" />
      </CardContent>
    </Card>
  )
}

function EmptyChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="min-h-[400px] flex items-center justify-center">
          <p className="text-muted-foreground">No pipeline data</p>
        </div>
      </CardContent>
    </Card>
  )
}
