import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle } from "lucide-react"
import type { AtRiskDonor } from "@/api/dashboard"

interface AtRiskDonorsProps {
  donors: AtRiskDonor[]
  totalCount: number
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
    year: "numeric",
  })
}

export function AtRiskDonors({ donors, totalCount, isLoading }: AtRiskDonorsProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            <div>
              <CardTitle>At-Risk Donors</CardTitle>
              <CardDescription>Haven't given in 60+ days</CardDescription>
            </div>
          </div>
          {totalCount > 5 && (
            <Button variant="link" size="sm" asChild className="p-0 h-auto">
              <Link to="/contacts?filter=at_risk">View all ({totalCount})</Link>
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
        ) : donors.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            No at-risk donors identified
          </p>
        ) : (
          <div className="space-y-1">
            {donors.map((donor) => (
              <Link
                key={donor.id}
                to={`/contacts/${donor.id}`}
                className="flex items-center justify-between py-2 border-b border-border last:border-0 hover:bg-muted/50 -mx-2 px-2 rounded"
              >
                <div>
                  <p className="font-medium">
                    {donor.first_name} {donor.last_name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Last gift: {formatDate(donor.last_gift_date)}
                  </p>
                </div>
                <span className="text-sm text-muted-foreground">
                  {formatCurrency(donor.total_given)} total
                </span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
