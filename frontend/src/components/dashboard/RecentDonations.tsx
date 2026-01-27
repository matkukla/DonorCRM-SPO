import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { RecentGift } from "@/api/dashboard"

interface RecentDonationsProps {
  donations: RecentGift[]
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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

export function RecentDonations({ donations, isLoading }: RecentDonationsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Donations</CardTitle>
        <CardDescription>Latest gifts received</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                <div className="h-4 w-16 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : donations.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            No recent donations
          </p>
        ) : (
          <div className="space-y-1">
            {donations.map((donation) => (
              <div
                key={donation.id}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div>
                  <Link
                    to={`/contacts/${donation.contact_id}`}
                    className="font-medium hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {donation.contact__first_name} {donation.contact__last_name}
                  </Link>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(donation.date)}
                  </p>
                </div>
                <span className="font-semibold text-primary">
                  {formatCurrency(donation.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
