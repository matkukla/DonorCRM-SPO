import { useMemo } from "react"
import { FunnelChart, Funnel, LabelList, Tooltip } from "recharts"
import { ChartContainer } from "@/components/ui/chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAdminConversionFunnel } from "@/hooks/useInsights"
import { CHART_COLORS } from "@/lib/chart-palette"

const FUNNEL_COLORS = CHART_COLORS

interface ConversionFunnelChartProps {
  dateParams?: { date_from?: string; date_to?: string }
  onStageClick?: (stage: string) => void
}

export function ConversionFunnelChart({ dateParams, onStageClick }: ConversionFunnelChartProps) {
  const { data, isLoading } = useAdminConversionFunnel(dateParams)

  const chartData = useMemo(() => {
    if (!data?.funnel) return []
    return data.funnel.map((stage, index) => ({
      name: stage.label,
      value: stage.count,
      percentage: stage.percentage,
      stage: stage.stage,
      fill: FUNNEL_COLORS[index % FUNNEL_COLORS.length],
    }))
  }, [data])

  const handleClick = (data: any) => {
    if (data.stage !== undefined && onStageClick) {
      onStageClick(data.stage ?? 'none')
    }
  }

  if (isLoading) return <ChartSkeleton />
  if (!chartData.length) return <EmptyChart />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
        <CardDescription>
          {data?.total_contacts_in_pipeline} contacts in pipeline. Click a stage to view contacts.
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
              onClick={handleClick}
              cursor="pointer"
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
