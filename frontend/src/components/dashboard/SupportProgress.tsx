import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { SupportProgress as SupportProgressType } from "@/api/dashboard"

interface SupportProgressProps {
  data: SupportProgressType | null
  isLoading?: boolean
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function SupportProgress({ data, isLoading }: SupportProgressProps) {
  const percentage = data ? Math.min(100, Math.round(data.percentage)) : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>Monthly Support Goal</CardTitle>
        <CardDescription>Progress toward your fundraising target</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <div className="h-4 bg-muted rounded animate-pulse" />
            <div className="h-8 bg-muted rounded animate-pulse" />
          </div>
        ) : !data || data.monthly_goal === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            Set a monthly goal in settings to track progress.
          </p>
        ) : (
          <div className="space-y-4">
            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">
                  {formatCurrency(data.current_monthly_support)} raised
                </span>
                <span className="font-medium">
                  {percentage}%
                </span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-500 rounded-full"
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{data.active_pledge_count} active pledges</span>
                <span>Goal: {formatCurrency(data.monthly_goal)}</span>
              </div>
            </div>

            {/* Gap indicator */}
            {data.gap > 0 && (
              <div className="pt-2 border-t border-border">
                <p className="text-sm">
                  <span className="text-muted-foreground">Remaining: </span>
                  <span className="font-semibold text-primary">
                    {formatCurrency(data.gap)}
                  </span>
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
