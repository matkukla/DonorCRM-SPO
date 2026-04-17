import { useMemo } from "react"
import { Link } from "react-router-dom"
import { AlertTriangle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAdminUserPerformance } from "@/hooks/useInsights"
import type { DashboardOverviewResponse, UserPerformanceItem } from "@/api/insights"

interface AlertsPanelProps {
  overview?: DashboardOverviewResponse
  isOverviewLoading?: boolean
  users?: UserPerformanceItem[]
  isUsersLoading?: boolean
}

interface CoachingAlert {
  id: string
  message: string
  severity: "high" | "medium" | "low"
  actionLink?: string
}

function computeAlerts(
  overview?: DashboardOverviewResponse,
  users?: UserPerformanceItem[]
): CoachingAlert[] {
  const alerts: CoachingAlert[] = []

  if (!overview || !users) {
    return alerts
  }

  // HIGH: Stalled contacts >20
  if (overview.stalled_contacts > 20) {
    alerts.push({
      id: "stalled-contacts-high",
      message: `${overview.stalled_contacts} contacts stalled >14 days across team`,
      severity: "high",
      actionLink: "/admin/analytics/stalled",
    })
  }

  // MEDIUM: Low conversion rate users
  users.forEach((user) => {
    if (user.conversion_rate < 10 && user.total_contacts >= 5) {
      alerts.push({
        id: `low-conversion-${user.id}`,
        message: `${user.name} has ${user.conversion_rate.toFixed(1)}% conversion rate`,
        severity: "medium",
        actionLink: `/admin/analytics/users/${user.id}`,
      })
    }
  })

  // MEDIUM: Users with contacts but no active journals
  users.forEach((user) => {
    if (user.active_journals === 0 && user.total_contacts > 0) {
      alerts.push({
        id: `no-journals-${user.id}`,
        message: `${user.name} has ${user.total_contacts} contacts but no active journals`,
        severity: "medium",
        actionLink: `/admin/analytics/users/${user.id}`,
      })
    }
  })

  // LOW: Team conversion rate below threshold
  if (overview.conversion_rate < 15) {
    alerts.push({
      id: "team-conversion-low",
      message: `Team conversion rate at ${overview.conversion_rate.toFixed(1)}% (below 15% threshold)`,
      severity: "low",
    })
  }

  // LOW: No active journals across team
  if (overview.active_journals === 0) {
    alerts.push({
      id: "no-active-journals",
      message: "No active journals across team",
      severity: "low",
    })
  }

  return alerts
}

const severityStyles = {
  high: "bg-red-50 dark:bg-red-950/50 border-red-100 dark:border-red-900/50 text-red-900 dark:text-red-200",
  medium: "bg-amber-50 dark:bg-amber-950/50 border-amber-100 dark:border-amber-900/50 text-amber-900 dark:text-amber-200",
  low: "bg-blue-50 dark:bg-blue-950/50 border-blue-100 dark:border-blue-900/50 text-blue-900 dark:text-blue-200",
}

export function AlertsPanel({
  overview,
  isOverviewLoading = false,
  users,
  isUsersLoading,
}: AlertsPanelProps) {
  // Only fetch if parent didn't pass `users`. When `users` is undefined on
  // first render (parent query not yet resolved), shouldFetchUsers=true and
  // this hook fires — but AdminAnalyticsDashboard already called
  // useAdminUserPerformance, so React Query deduplicates to the same cache
  // key and no extra HTTP request is made. Once the parent query resolves,
  // shouldFetchUsers flips to false and this hook becomes a no-op.
  const shouldFetchUsers = users === undefined
  const { data: fetchedUsersData, isLoading: fetchedUsersLoading } = useAdminUserPerformance({
    enabled: shouldFetchUsers,
  })

  const effectiveUsers = users ?? fetchedUsersData?.users
  const effectiveUsersLoading = shouldFetchUsers ? fetchedUsersLoading : (isUsersLoading ?? false)

  const alerts = useMemo(
    () => computeAlerts(overview, effectiveUsers),
    [overview, effectiveUsers]
  )

  const isLoading = isOverviewLoading || effectiveUsersLoading

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <CardTitle>Coaching Alerts</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            All clear! No coaching alerts at this time.
          </p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  "p-4 border rounded-lg",
                  severityStyles[alert.severity]
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm font-medium flex-1">{alert.message}</p>
                  {alert.actionLink && (
                    <Button variant="link" size="sm" asChild className="p-0 h-auto shrink-0">
                      <Link to={alert.actionLink}>View details</Link>
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
