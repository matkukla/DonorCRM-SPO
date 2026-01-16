import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, Clock, CheckSquare, Heart } from "lucide-react"
import type { OverdueTask, LatePledge, ThankYouContact } from "@/api/dashboard"

interface NeedsAttentionProps {
  overdueTasks: OverdueTask[]
  overdueTaskCount: number
  latePledges: LatePledge[]
  latePledgeCount: number
  thankYouNeeded: ThankYouContact[]
  thankYouCount: number
  isLoading?: boolean
}

function formatCurrency(amount: string | number): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

export function NeedsAttention({
  overdueTasks,
  overdueTaskCount,
  latePledges,
  latePledgeCount,
  thankYouNeeded,
  thankYouCount,
  isLoading,
}: NeedsAttentionProps) {
  const hasItems = overdueTaskCount > 0 || latePledgeCount > 0 || thankYouCount > 0

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <div>
            <CardTitle>Needs Attention</CardTitle>
            <CardDescription>Items requiring your action</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : !hasItems ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            All caught up! No items need attention.
          </p>
        ) : (
          <div className="space-y-4">
            {/* Overdue Tasks */}
            {overdueTaskCount > 0 && (
              <div className="p-4 bg-red-50 border border-red-100 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckSquare className="h-4 w-4 text-red-600" />
                    <span className="font-medium text-red-900">
                      {overdueTaskCount} Overdue Task{overdueTaskCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-red-600 p-0 h-auto">
                    <Link to="/tasks?filter=overdue">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-red-800">
                  {overdueTasks.slice(0, 3).map((task) => (
                    <li key={task.id} className="truncate">
                      {task.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Late Pledges */}
            {latePledgeCount > 0 && (
              <div className="p-4 bg-amber-50 border border-amber-100 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-amber-600" />
                    <span className="font-medium text-amber-900">
                      {latePledgeCount} Late Pledge{latePledgeCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-amber-600 p-0 h-auto">
                    <Link to="/pledges?filter=late">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-amber-800">
                  {latePledges.slice(0, 3).map((pledge) => (
                    <li key={pledge.id}>
                      {formatCurrency(pledge.amount)} ({pledge.days_late} days late)
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Thank You Queue */}
            {thankYouCount > 0 && (
              <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Heart className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-blue-900">
                      {thankYouCount} Thank You{thankYouCount !== 1 ? "s" : ""} Needed
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-blue-600 p-0 h-auto">
                    <Link to="/contacts?filter=needs_thank_you">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-blue-800">
                  {thankYouNeeded.slice(0, 3).map((contact) => (
                    <li key={contact.id}>
                      {contact.first_name} {contact.last_name}
                      {contact.last_gift_amount && (
                        <span className="text-blue-600 ml-1">
                          ({formatCurrency(contact.last_gift_amount)})
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
