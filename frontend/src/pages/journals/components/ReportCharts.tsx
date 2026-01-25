import { useMemo } from "react"
import { BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useDecisionTrends, useStageActivity, usePipelineBreakdown, useNextStepsQueue } from "@/hooks/useJournals"
import { STAGE_LABELS } from "@/types/journals"
import { formatDistanceToNow } from "date-fns"

const decisionTrendsConfig = {
  count: { label: "Decisions", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig

const stageActivityConfig = {
  contact: { label: "Contact", color: "hsl(var(--chart-1))" },
  meet: { label: "Meet", color: "hsl(var(--chart-2))" },
  close: { label: "Close", color: "hsl(var(--chart-3))" },
  decision: { label: "Decision", color: "hsl(var(--chart-4))" },
  thank: { label: "Thank", color: "hsl(var(--chart-5))" },
  next_steps: { label: "Next Steps", color: "hsl(var(--chart-6))" },
} satisfies ChartConfig

const STAGE_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
]

export function DecisionTrendsChart() {
  const { data, isLoading } = useDecisionTrends()

  if (isLoading) return <ChartSkeleton title="Decision Trends" />
  if (!data?.length) return <EmptyChart title="Decision Trends" message="No decisions recorded yet" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision Trends</CardTitle>
        <CardDescription>Decisions made over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={decisionTrendsConfig} className="min-h-[300px] w-full">
          <BarChart data={data}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="month" tickLine={false} tickMargin={10} axisLine={false} />
            <YAxis />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="count" fill="var(--color-count)" radius={4} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function StageActivityChart() {
  const { data, isLoading } = useStageActivity()

  if (isLoading) return <ChartSkeleton title="Stage Activity" />
  if (!data?.length) return <EmptyChart title="Stage Activity" message="No stage events recorded yet" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stage Activity</CardTitle>
        <CardDescription>Events by stage over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={stageActivityConfig} className="min-h-[300px] w-full">
          <AreaChart data={data}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickLine={false} tickMargin={10} axisLine={false} />
            <YAxis />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Area dataKey="contact" fill="var(--color-contact)" stroke="var(--color-contact)" stackId="1" />
            <Area dataKey="meet" fill="var(--color-meet)" stroke="var(--color-meet)" stackId="1" />
            <Area dataKey="close" fill="var(--color-close)" stroke="var(--color-close)" stackId="1" />
            <Area dataKey="decision" fill="var(--color-decision)" stroke="var(--color-decision)" stackId="1" />
            <Area dataKey="thank" fill="var(--color-thank)" stroke="var(--color-thank)" stackId="1" />
            <Area dataKey="next_steps" fill="var(--color-next_steps)" stroke="var(--color-next_steps)" stackId="1" />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function PipelineBreakdownChart() {
  const { data, isLoading } = usePipelineBreakdown()

  const chartData = useMemo(() => {
    if (!data) return []
    return data.map((item, index) => ({
      ...item,
      fill: STAGE_COLORS[index % STAGE_COLORS.length],
      name: STAGE_LABELS[item.stage] || item.stage,
    }))
  }, [data])

  if (isLoading) return <ChartSkeleton title="Pipeline Breakdown" />
  if (!chartData.length) return <EmptyChart title="Pipeline Breakdown" message="No contacts in pipeline yet" />

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Breakdown</CardTitle>
        <CardDescription>Contacts by current stage</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={stageActivityConfig} className="min-h-[300px] w-full">
          <PieChart>
            <ChartTooltip content={<ChartTooltipContent />} />
            <Pie
              data={chartData}
              dataKey="count"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={(props) => {
                const entry = chartData[props.index]
                return `${entry.name}: ${entry.count}`
              }}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function NextStepsQueue() {
  const { data, isLoading } = useNextStepsQueue()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Next Steps Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data?.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Next Steps Queue</CardTitle>
          <CardDescription>Upcoming actions across all contacts</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">No pending next steps</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Next Steps Queue</CardTitle>
        <CardDescription>Upcoming actions across all contacts</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.map((step) => (
            <div key={step.id} className="flex items-start justify-between py-2 border-b last:border-0">
              <div>
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">
                  {step.contact_name} &middot; {step.journal_name}
                </p>
              </div>
              {step.due_date && (
                <Badge variant={new Date(step.due_date) < new Date() ? "destructive" : "secondary"}>
                  {formatDistanceToNow(new Date(step.due_date), { addSuffix: true })}
                </Badge>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ChartSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="min-h-[300px] bg-muted rounded animate-pulse" />
      </CardContent>
    </Card>
  )
}

function EmptyChart({ title, message }: { title: string; message: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="min-h-[300px] flex items-center justify-center">
          <p className="text-muted-foreground">{message}</p>
        </div>
      </CardContent>
    </Card>
  )
}
