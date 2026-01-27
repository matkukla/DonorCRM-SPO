import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Clock, BookOpen } from "lucide-react"
import type { LateDonation } from "@/api/dashboard"

interface LateDonationsProps {
  donations: LateDonation[]
  totalCount: number
  isLoading?: boolean
  onQuickLog?: (contactId: string) => void
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No gifts yet"
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export function LateDonations({ donations, totalCount, isLoading, onQuickLog }: LateDonationsProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-destructive" />
            <div>
              <CardTitle>Late Donations</CardTitle>
              <CardDescription>Active pledges past due</CardDescription>
            </div>
          </div>
          {totalCount > 5 && (
            <Button variant="link" size="sm" asChild className="p-0 h-auto">
              <Link to="/pledges?filter=late">View all ({totalCount})</Link>
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                <div className="h-4 w-20 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : donations.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            All pledges are on track
          </p>
        ) : (
          <div className="space-y-1">
            {donations.map((donation) => (
              <div
                key={donation.id}
                className="flex items-center justify-between py-2 border-b border-border last:border-0 -mx-2 px-2 rounded"
              >
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/contacts/${donation.contact_id}`}
                    className="font-medium hover:underline"
                  >
                    {donation.contact_name}
                  </Link>
                  <p className="text-sm text-muted-foreground">
                    {formatCurrency(donation.amount)}/mo &middot; Last: {formatDate(donation.last_gift_date)}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-2 shrink-0">
                  <Badge variant="destructive">{donation.days_late}d late</Badge>
                  {onQuickLog && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => onQuickLog(donation.contact_id)}
                    >
                      <BookOpen className="h-3.5 w-3.5 mr-1" />
                      Log
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
