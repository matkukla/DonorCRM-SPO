import { useState } from "react"
import { NavLink, useSearchParams } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAdminDashboardOverview } from "@/hooks/useInsights"
import { cn } from "@/lib/utils"
import type { DateRange } from "@/lib/date-presets"
import { dateRangeToParams } from "@/lib/date-presets"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import { parseISO, isValid, format } from "date-fns"
import { TeamActivityTable } from "./components/TeamActivityTable"
import { AlertsPanel } from "./components/AlertsPanel"
import { TrendCharts } from "./components/TrendCharts"
import { ConversionFunnelChart } from "./components/ConversionFunnelChart"
import { FunnelDrilldownPanel } from "./components/FunnelDrilldownPanel"
import { UserDrilldownPanel } from "./components/UserDrilldownPanel"
import { TimePeriodComparison } from "./components/TimePeriodComparison"
import { UserComparison } from "./components/UserComparison"
import { MPDOverviewTable } from "@/components/mpd/MPDOverviewTable"

export default function AdminAnalyticsDashboard() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [dateRange, setDateRange] = useState<DateRange | null>(() => {
    // Read and validate URL params on mount
    const dateFrom = searchParams.get('date_from')
    const dateTo = searchParams.get('date_to')

    if (dateFrom && dateTo) {
      const fromDate = parseISO(dateFrom)
      const toDate = parseISO(dateTo)

      // Validate both dates are valid and from is before to
      if (isValid(fromDate) && isValid(toDate) && fromDate <= toDate) {
        return { from: fromDate, to: toDate }
      }
      // Invalid dates: clear params
    }

    return null
  })

  const dateParams = dateRangeToParams(dateRange)

  const { data, isLoading, error } = useAdminDashboardOverview(dateParams)

  const [funnelDrilldown, setFunnelDrilldown] = useState<{
    open: boolean
    stage: string | null
  }>({ open: false, stage: null })

  const [userDrilldown, setUserDrilldown] = useState<{
    open: boolean
    userId: string | null
  }>({ open: false, userId: null })

  const handleStageClick = (stage: string) => {
    setFunnelDrilldown({ open: true, stage })
  }

  const handleFunnelClose = () => {
    setFunnelDrilldown({ open: false, stage: null })
  }

  const handleUserDrilldown = (userId: string) => {
    setUserDrilldown({ open: true, userId })
  }

  const handleUserDrilldownClose = () => {
    setUserDrilldown({ open: false, userId: null })
  }

  const handleDateRangeChange = (newRange: DateRange | null) => {
    setDateRange(newRange)

    // Sync URL params
    if (newRange?.from && newRange?.to) {
      setSearchParams({
        date_from: format(newRange.from, 'yyyy-MM-dd'),
        date_to: format(newRange.to, 'yyyy-MM-dd'),
      })
    } else {
      setSearchParams({}) // Clear params
    }
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Admin Sub-Navigation */}
          <div className="flex gap-4 border-b border-border pb-2">
            <NavLink
              to="/admin"
              end
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Users
            </NavLink>
            <NavLink
              to="/admin/analytics"
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Analytics
            </NavLink>
            <NavLink
              to="/admin/assignments"
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Assignments
            </NavLink>
          </div>

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Analytics Dashboard</h1>
              <p className="text-muted-foreground mt-1">
                Organization-wide fundraising analytics
              </p>
            </div>
            <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />
          </div>

          {/* Summary Cards Row */}
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-muted rounded-lg animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <p className="text-destructive text-sm">Failed to load dashboard summary. Please try again.</p>
            </div>
          ) : data ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Total Contacts
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{data.total_contacts}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Active Journals
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{data.active_journals}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Stalled Contacts
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{data.stalled_contacts}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Conversion Rate
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{data.conversion_rate.toFixed(1)}%</div>
                </CardContent>
              </Card>
            </div>
          ) : null}

          {/* Donations Card */}
          {data && (
            <Card>
              <CardHeader>
                <CardTitle>Donations (12 Months)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Amount</p>
                    <p className="text-2xl font-bold">
                      {(data.donations_12m.total_amount / 100).toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD'
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Donation Count</p>
                    <p className="text-2xl font-bold">{data.donations_12m.total_count}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Charts Row: Trend Charts + Conversion Funnel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TrendCharts dateParams={dateParams} />
            <ConversionFunnelChart dateParams={dateParams} onStageClick={handleStageClick} />
          </div>

          {/* Activity and Alerts Row: Team Activity Table (2/3) + Alerts Panel (1/3) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <TeamActivityTable dateParams={dateParams} onUserDrilldown={handleUserDrilldown} />
            </div>
            <div className="lg:col-span-1">
              <AlertsPanel />
            </div>
          </div>

          {/* Comparison Row: Time Period (1/2) + User Comparison (1/2) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TimePeriodComparison dateParams={dateParams} />
            <UserComparison />
          </div>

          {/* MPD Overview - Full Width */}
          <MPDOverviewTable />
        </div>

        {/* Drill-down Panels */}
        <FunnelDrilldownPanel
          open={funnelDrilldown.open}
          stage={funnelDrilldown.stage}
          onClose={handleFunnelClose}
        />
        <UserDrilldownPanel
          open={userDrilldown.open}
          userId={userDrilldown.userId}
          onClose={handleUserDrilldownClose}
        />
      </Container>
    </Section>
  )
}
