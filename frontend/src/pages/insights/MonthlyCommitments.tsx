import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useMonthlyCommitments } from "@/hooks/useInsights"

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

export default function MonthlyCommitments() {
  const { data, isLoading, error } = useMonthlyCommitments()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Monthly Commitments</h1>
            <p className="text-muted-foreground mt-1">
              Active recurring pledge summary
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
              {/* Summary Cards */}
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Monthly Total</CardDescription>
                    <CardTitle className="text-3xl">{formatCurrency(data.total_monthly)}</CardTitle>
                  </CardHeader>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Annual Total</CardDescription>
                    <CardTitle className="text-3xl">{formatCurrency(data.total_annual)}</CardTitle>
                  </CardHeader>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Active Pledges</CardDescription>
                    <CardTitle className="text-3xl">{data.active_count}</CardTitle>
                  </CardHeader>
                </Card>
              </div>

              {/* Breakdown by Frequency */}
              {data.by_frequency.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>By Frequency</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex gap-4 flex-wrap">
                      {data.by_frequency.map((freq) => (
                        <div key={freq.frequency} className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg">
                          <span className="font-medium">{frequencyLabels[freq.frequency] || freq.frequency}</span>
                          <Badge variant="secondary">{freq.count}</Badge>
                          <span className="text-muted-foreground">({formatCurrency(freq.monthly_total)}/mo)</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Pledges Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Active Pledges</CardTitle>
                  <CardDescription>{data.active_count} pledges</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.pledges.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No active pledges found.
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Contact</TableHead>
                          <TableHead>Frequency</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                          <TableHead className="text-right">Monthly Equiv.</TableHead>
                          <TableHead>Start Date</TableHead>
                          <TableHead>Last Fulfilled</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.pledges.map((pledge) => (
                          <TableRow key={pledge.id}>
                            <TableCell>
                              <Link
                                to={`/contacts/${pledge.contact_id}`}
                                className="font-medium hover:underline text-primary"
                              >
                                {pledge.contact_name}
                              </Link>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {frequencyLabels[pledge.frequency] || pledge.frequency}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{formatCurrency(pledge.amount)}</TableCell>
                            <TableCell className="text-right">{formatCurrency(pledge.monthly_equivalent)}</TableCell>
                            <TableCell>{new Date(pledge.start_date).toLocaleDateString()}</TableCell>
                            <TableCell>
                              {pledge.last_fulfilled_date
                                ? new Date(pledge.last_fulfilled_date).toLocaleDateString()
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
