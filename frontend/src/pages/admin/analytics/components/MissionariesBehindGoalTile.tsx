import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useMissionariesBehindGoal } from "@/hooks/useAdminAnalytics"
import { clampPercentage, formatCents } from "@/lib/format"

interface MissionariesBehindGoalTileProps {
  limit?: number
  onUserClick?: (userId: string) => void
}

export function MissionariesBehindGoalTile({
  limit = 10,
  onUserClick,
}: MissionariesBehindGoalTileProps) {
  const { data, isLoading, error } = useMissionariesBehindGoal({ limit })

  if (isLoading) {
    return (
      <Card data-testid="missionaries-behind-tile" data-state="loading">
        <CardHeader>
          <CardTitle>Missionaries Behind Goal</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card data-testid="missionaries-behind-tile" data-state="error">
        <CardHeader>
          <CardTitle>Missionaries Behind Goal</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
            <p className="text-destructive text-sm">Failed to load missionary pace.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { missionaries, total_excluded_no_goal, total_missionaries } = data

  return (
    <Card data-testid="missionaries-behind-tile" data-state="ready">
      <CardHeader>
        <CardTitle>Missionaries Behind Goal</CardTitle>
        <CardDescription>
          Sorted by this-month pace. {total_missionaries} active missionaries.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {missionaries.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-muted-foreground">
              All missionaries on pace this month 🎯
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="text-right">Monthly Goal</TableHead>
                <TableHead className="text-right">This Month</TableHead>
                <TableHead className="w-32">Pace</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {missionaries.map((m) => {
                const pace = clampPercentage(m.pace_percentage, 0, 150)
                const barValue = clampPercentage(pace, 0, 100)
                return (
                  <TableRow
                    key={m.user_id}
                    className={onUserClick ? "cursor-pointer" : ""}
                    onClick={() => onUserClick?.(m.user_id)}
                    data-testid="missionaries-behind-row"
                  >
                    <TableCell>
                      <div className="font-medium">{m.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{m.email}</div>
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCents(m.monthly_goal_cents, { whole: true })}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCents(m.this_month_raised_cents, { whole: true })}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={barValue} className="h-2 flex-1" />
                        <span className="text-xs font-medium tabular-nums w-10 text-right">
                          {pace.toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
        {total_excluded_no_goal > 0 && (
          <p className="text-xs text-muted-foreground mt-4">
            {total_excluded_no_goal} missionaries excluded (no goal set)
          </p>
        )}
      </CardContent>
    </Card>
  )
}
