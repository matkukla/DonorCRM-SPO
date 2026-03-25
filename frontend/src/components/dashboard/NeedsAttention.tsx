import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, CheckSquare, Clock, Heart, Megaphone } from "lucide-react"
import type { OverdueTask, LatePledge, ThankYouContact } from "@/api/dashboard"

interface NeedsAttentionProps {
  overdueTasks: OverdueTask[]
  overdueTaskCount: number
  tasksDueToday: OverdueTask[]
  tasksDueTodayCount: number
  broadcastTasks: OverdueTask[]
  broadcastTaskCount: number
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
  tasksDueToday,
  tasksDueTodayCount,
  broadcastTasks,
  broadcastTaskCount,
  thankYouNeeded,
  thankYouCount,
  isLoading,
}: NeedsAttentionProps) {
  const hasItems = overdueTaskCount > 0 || tasksDueTodayCount > 0 || broadcastTaskCount > 0 || thankYouCount > 0

  return (
    <Card>
      <CardHeader className="p-4 pl-7">
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="h-4 w-4 text-amber-500 dark:text-amber-400 shrink-0" />
          <div>
            <CardTitle>Needs Attention</CardTitle>
            <CardDescription>Items requiring your action</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pl-7 pt-0 pb-4">
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
              <div className="p-4 bg-red-50 dark:bg-red-950/50 border border-red-100 dark:border-red-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckSquare className="h-4 w-4 text-red-600 dark:text-red-400" />
                    <span className="text-sm font-medium text-red-900 dark:text-red-200">
                      {overdueTaskCount} Overdue Task{overdueTaskCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-red-600 dark:text-red-400 p-0 h-auto">
                    <Link to="/tasks?filter=overdue">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-red-800 dark:text-red-300">
                  {overdueTasks.slice(0, 3).map((task) => (
                    <li key={task.id} className="truncate">
                      {task.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Tasks Due Today */}
            {tasksDueTodayCount > 0 && (
              <div className="p-4 bg-amber-50 dark:bg-amber-950/50 border border-amber-100 dark:border-amber-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    <span className="text-sm font-medium text-amber-900 dark:text-amber-200">
                      {tasksDueTodayCount} Task{tasksDueTodayCount !== 1 ? "s" : ""} Due Today
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-amber-600 dark:text-amber-400 p-0 h-auto">
                    <Link to="/tasks">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-300">
                  {tasksDueToday.slice(0, 3).map((task) => (
                    <li key={task.id} className="truncate">
                      {task.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Broadcast Tasks */}
            {broadcastTaskCount > 0 && (
              <div className="p-4 bg-purple-50 dark:bg-purple-950/50 border border-purple-100 dark:border-purple-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Megaphone className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-sm font-medium text-purple-900 dark:text-purple-200">
                      {broadcastTaskCount} Broadcast Task{broadcastTaskCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-purple-600 dark:text-purple-400 p-0 h-auto">
                    <Link to="/tasks">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-purple-800 dark:text-purple-300">
                  {broadcastTasks.slice(0, 3).map((task) => (
                    <li key={task.id} className="truncate">
                      {task.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Thank You Queue */}
            {thankYouCount > 0 && (
              <div className="p-4 bg-blue-50 dark:bg-blue-950/50 border border-blue-100 dark:border-blue-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Heart className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span className="text-sm font-medium text-blue-900 dark:text-blue-200">
                      {thankYouCount} Thank You{thankYouCount !== 1 ? "s" : ""} Needed
                    </span>
                  </div>
                  <Button variant="link" size="sm" asChild className="text-blue-600 dark:text-blue-400 p-0 h-auto">
                    <Link to="/contacts?filter=needs_thank_you">View all</Link>
                  </Button>
                </div>
                <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-300">
                  {thankYouNeeded.slice(0, 3).map((contact) => (
                    <li key={contact.id}>
                      {contact.first_name} {contact.last_name}
                      {contact.last_gift_amount && (
                        <span className="text-blue-600 dark:text-blue-400 ml-1">
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
