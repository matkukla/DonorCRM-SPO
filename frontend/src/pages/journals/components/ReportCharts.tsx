import { useState, useMemo } from "react"
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import type { DateRange } from "@/lib/date-presets"
import { dateRangeToParams } from "@/lib/date-presets"
import { useJournalReport } from "@/hooks/useJournals"
import { STAGE_LABELS } from "@/types/journals"
import type { PipelineStage } from "@/types/journals"
import {
  Users,
  FileCheck,
  DollarSign,
  Clock,
  AlertTriangle,
  ListTodo,
} from "lucide-react"

interface JournalReportProps {
  journalId: string
  goalAmount: string
}

const stageChartConfig = {
  count: { label: "Contacts" },
  contact: { label: "Contact", color: "hsl(var(--chart-1))" },
  scheduled: { label: "Scheduled", color: "hsl(200 60% 50%)" },
  meet: { label: "Meet", color: "hsl(var(--chart-2))" },
  close: { label: "Close", color: "hsl(var(--chart-3))" },
  decision: { label: "Decision", color: "hsl(var(--chart-4))" },
  thank: { label: "Thank You", color: "hsl(var(--chart-5))" },
  next_steps: { label: "Next Steps", color: "hsl(var(--chart-6))" },
} satisfies ChartConfig

const STAGE_COLOR_MAP: Record<string, string> = {
  contact: "hsl(var(--chart-1))",
  scheduled: "hsl(200 60% 50%)",
  meet: "hsl(var(--chart-2))",
  close: "hsl(var(--chart-3))",
  decision: "hsl(var(--chart-4))",
  thank: "hsl(var(--chart-5))",
  next_steps: "hsl(var(--chart-6))",
  none: "hsl(var(--muted-foreground))",
}

const decisionChartConfig = {
  value: { label: "Decisions" },
  active: { label: "Active", color: "hsl(var(--chart-1))" },
  pending: { label: "Pending", color: "hsl(var(--chart-2))" },
  paused: { label: "Paused", color: "hsl(var(--chart-3))" },
  declined: { label: "Declined", color: "hsl(var(--chart-4))" },
} satisfies ChartConfig

const STATUS_COLOR_MAP: Record<string, string> = {
  active: "hsl(var(--chart-1))",
  pending: "hsl(var(--chart-2))",
  paused: "hsl(var(--chart-3))",
  declined: "hsl(var(--chart-4))",
}

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  pending: "Pending",
  paused: "Paused",
  declined: "Declined",
}

function formatCurrency(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  })
}

export function JournalReport({ journalId, goalAmount }: JournalReportProps) {
  const [dateRange, setDateRange] = useState<DateRange | null>(null)
  const dateParams = dateRangeToParams(dateRange) as Record<string, string>

  const { data, isLoading } = useJournalReport(journalId, dateParams)

  // Bar chart data
  const stageBarData = useMemo(() => {
    if (!data?.stage_distribution) return []
    return data.stage_distribution.map((item) => ({
      name:
        item.stage && item.stage !== "none"
          ? STAGE_LABELS[item.stage as PipelineStage] || item.stage
          : "Not Started",
      count: item.count,
      fill: STAGE_COLOR_MAP[item.stage ?? "none"] || STAGE_COLOR_MAP.none,
    }))
  }, [data])

  // Donut chart data
  const decisionDonutData = useMemo(() => {
    if (!data?.decision_status) return []
    return data.decision_status.map((item) => ({
      name: STATUS_LABELS[item.status] || item.status,
      value: item.count,
      fill: STATUS_COLOR_MAP[item.status] || "hsl(var(--muted-foreground))",
    }))
  }, [data])

  // Goal progress
  const confirmed = data ? parseFloat(data.metrics.confirmed_amount) : 0
  const goal = parseFloat(goalAmount) || 0
  const percentage = goal === 0 ? 0 : Math.min(100, Math.round((confirmed / goal) * 100))

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-end">
          <div className="h-10 w-48 animate-pulse bg-muted rounded" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 animate-pulse bg-muted rounded" />
          ))}
        </div>
        <div className="h-20 animate-pulse bg-muted rounded" />
        <div className="grid gap-6 md:grid-cols-2">
          <div className="h-80 animate-pulse bg-muted rounded" />
          <div className="h-80 animate-pulse bg-muted rounded" />
        </div>
      </div>
    )
  }

  // Empty state
  if (data && data.metrics.total_contacts === 0) {
    return (
      <div className="space-y-6">
        <div className="flex justify-end">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          No contacts in this journal yet.
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Date range picker */}
      <div className="flex justify-end">
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      {/* Metric cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Contacts</CardTitle>
            <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.metrics.total_contacts}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">With Decisions</CardTitle>
            <div className="h-8 w-8 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <FileCheck className="h-4 w-4 text-green-600 dark:text-green-400" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.metrics.with_decisions}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confirmed $</CardTitle>
            <div className="h-8 w-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(parseFloat(data.metrics.confirmed_amount))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <div className="h-8 w-8 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(parseFloat(data.metrics.pending_amount))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Goal progress bar */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Goal Progress</CardTitle>
          <CardDescription>
            {formatCurrency(confirmed)} of {formatCurrency(goal)} confirmed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Progress value={percentage} className="h-3" />
          <p className="text-xs text-muted-foreground mt-1">{percentage}% of goal</p>
        </CardContent>
      </Card>

      {/* Charts row */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Contacts by Stage Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Contacts by Stage</CardTitle>
            <CardDescription>Distribution across pipeline stages</CardDescription>
          </CardHeader>
          <CardContent>
            {stageBarData.length > 0 ? (
              <ChartContainer config={stageChartConfig} className="min-h-[300px] w-full">
                <BarChart data={stageBarData}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    tickMargin={10}
                    axisLine={false}
                  />
                  <YAxis allowDecimals={false} />
                  <ChartTooltip isAnimationActive={false} content={<ChartTooltipContent />} />
                  <Bar dataKey="count" radius={4}>
                    {stageBarData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="min-h-[300px] flex items-center justify-center">
                <p className="text-muted-foreground">No stage data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Decision Status Donut Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Decision Status</CardTitle>
            <CardDescription>Breakdown of decision outcomes</CardDescription>
          </CardHeader>
          <CardContent>
            {decisionDonutData.length > 0 ? (
              <ChartContainer config={decisionChartConfig} className="min-h-[300px] w-full">
                <PieChart>
                  <ChartTooltip isAnimationActive={false} content={<ChartTooltipContent nameKey="name" />} />
                  <Pie
                    data={decisionDonutData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {decisionDonutData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                </PieChart>
              </ChartContainer>
            ) : (
              <div className="min-h-[300px] flex items-center justify-center">
                <p className="text-muted-foreground">No decisions recorded yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Conditional alerts */}
      {data.alerts.stalled_contacts > 0 && (
        <Card className="border-orange-500/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              Stalled Contacts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {data.alerts.stalled_contacts} contact(s) have had no activity in the last 30 days
            </p>
          </CardContent>
        </Card>
      )}

      {data.alerts.open_next_steps > 0 && (
        <Card className="border-blue-500/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <ListTodo className="h-4 w-4 text-blue-500" />
              Open Next Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {data.alerts.open_next_steps} next step(s) still pending across contacts
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
