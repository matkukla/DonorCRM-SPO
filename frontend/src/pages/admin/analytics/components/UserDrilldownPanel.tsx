import { Link } from "react-router-dom"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useAdminUserDrilldown } from "@/hooks/useInsights"
import { cn } from "@/lib/utils"

interface UserDrilldownPanelProps {
  open: boolean
  userId: string | null
  onClose: () => void
}

export function UserDrilldownPanel({ open, userId, onClose }: UserDrilldownPanelProps) {
  const { data, isLoading } = useAdminUserDrilldown(userId)

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        {isLoading ? (
          <div className="space-y-6">
            <div className="h-16 bg-muted rounded animate-pulse" />
            <div className="grid grid-cols-2 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-24 bg-muted rounded animate-pulse" />
              ))}
            </div>
            <div className="h-48 bg-muted rounded animate-pulse" />
          </div>
        ) : data ? (
          <div className="space-y-6">
            <SheetHeader>
              <SheetTitle>{data.user.name}</SheetTitle>
              <SheetDescription>
                {data.user.email} • {data.user.role}
              </SheetDescription>
            </SheetHeader>

            {/* Key Stats Grid */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Key Stats</h3>
              <div className="grid grid-cols-2 gap-3">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Total Contacts
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">{data.stats.total_contacts}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Active Journals
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">{data.stats.active_journals}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Decisions Logged
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">{data.stats.decisions_logged}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Conversion Rate
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">
                      {data.stats.conversion_rate.toFixed(1)}%
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">
                      Total Donations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xl font-bold">
                      {(data.stats.total_donations / 100).toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD',
                      })}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {data.stats.donation_count} donations
                    </p>
                  </CardContent>
                </Card>

                <Card className={cn(
                  data.stats.stalled_contacts > 0 && "border-amber-500 bg-amber-50/50 dark:bg-amber-950/20"
                )}>
                  <CardHeader className="pb-2">
                    <CardTitle className={cn(
                      "text-xs font-medium",
                      data.stats.stalled_contacts > 0 ? "text-amber-600 dark:text-amber-400" : "text-muted-foreground"
                    )}>
                      Stalled Contacts
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={cn(
                      "text-xl font-bold",
                      data.stats.stalled_contacts > 0 && "text-amber-600 dark:text-amber-400"
                    )}>
                      {data.stats.stalled_contacts}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Recent Journals */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Recent Journals</h3>
              {data.journals.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No active journals
                </p>
              ) : (
                <div className="rounded-lg border">
                  <Table aria-label="User journals">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead className="text-right">Members</TableHead>
                        <TableHead className="text-right">Decisions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.journals.map((journal) => (
                        <TableRow key={journal.id}>
                          <TableCell className="font-medium">{journal.name}</TableCell>
                          <TableCell className="text-right">
                            {journal.active_member_count}/{journal.member_count}
                          </TableCell>
                          <TableCell className="text-right">{journal.decision_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Quick Actions</h3>
              <Button asChild variant="outline" className="w-full">
                <Link to={`/admin/analytics/users/${data.user.id}`}>
                  View Full User Detail
                </Link>
              </Button>
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
