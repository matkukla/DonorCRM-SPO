import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useLateDonations } from "@/hooks/useInsights"
import { AlertCircle } from "lucide-react"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

const frequencyLabels: Record<string, string> = {
  monthly: "Monthly",
  quarterly: "Quarterly",
  semi_annual: "Semi-Annual",
  annual: "Annual",
}

function getDaysLateSeverity(daysLate: number): "default" | "secondary" | "destructive" {
  if (daysLate > 30) return "destructive"
  if (daysLate > 14) return "default"
  return "secondary"
}

export default function LateDonations() {
  const { data, isLoading, error } = useLateDonations()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Late Donations</h1>
            <p className="text-muted-foreground mt-1">
              Active pledges with overdue expected gifts
            </p>
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load data. Please try again.
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              Loading...
            </div>
          ) : data && (
            <>
              {/* Summary */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-destructive" />
                    <CardTitle>Overdue Pledges</CardTitle>
                  </div>
                  <CardDescription>
                    {data.total_count} pledges with late donations
                  </CardDescription>
                </CardHeader>
              </Card>

              {/* Late Donations Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Late Donations</CardTitle>
                </CardHeader>
                <CardContent>
                  {data.late_donations.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No late donations! All pledges are on track.
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Contact</TableHead>
                          <TableHead>Frequency</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                          <TableHead>Days Late</TableHead>
                          <TableHead>Last Gift</TableHead>
                          <TableHead>Expected</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.late_donations.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell>
                              <Link
                                to={`/contacts/${item.contact_id}`}
                                className="font-medium hover:underline text-primary"
                              >
                                {item.contact_name}
                              </Link>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {frequencyLabels[item.frequency] || item.frequency}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
                            <TableCell>
                              <Badge variant={getDaysLateSeverity(item.days_late)}>
                                {item.days_late} days
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {item.last_gift_date
                                ? new Date(item.last_gift_date).toLocaleDateString()
                                : "Never"}
                            </TableCell>
                            <TableCell>
                              {item.next_expected_date
                                ? new Date(item.next_expected_date).toLocaleDateString()
                                : "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </Container>
    </Section>
  )
}
