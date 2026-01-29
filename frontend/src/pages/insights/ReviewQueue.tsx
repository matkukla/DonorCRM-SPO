import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useReviewQueue } from "@/hooks/useInsights"
import { ClipboardCheck } from "lucide-react"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export default function ReviewQueue() {
  const { data, isLoading, error } = useReviewQueue()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Review Queue</h1>
            <p className="text-muted-foreground mt-1">
              Items pending admin review
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
                    <ClipboardCheck className="h-5 w-5 text-muted-foreground" />
                    <CardTitle>Pending Review</CardTitle>
                  </div>
                  <CardDescription>
                    {data.total_count} items need attention
                  </CardDescription>
                </CardHeader>
              </Card>

              {/* Queue Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Review Items</CardTitle>
                </CardHeader>
                <CardContent>
                  {data.items.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No items pending review.
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Type</TableHead>
                          <TableHead>Item</TableHead>
                          <TableHead>Contact</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                          <TableHead>Date</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.items.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell>
                              <Badge variant="outline">
                                {item.type === "thank_you" ? "Thank You" : item.type}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-medium">{item.title}</TableCell>
                            <TableCell>
                              <Link
                                to={`/contacts/${item.contact_id}`}
                                className="hover:underline text-primary"
                              >
                                {item.contact_name}
                              </Link>
                            </TableCell>
                            <TableCell className="text-right">
                              {item.last_gift_amount
                                ? formatCurrency(item.last_gift_amount)
                                : "—"}
                            </TableCell>
                            <TableCell>
                              {item.last_gift_date
                                ? new Date(item.last_gift_date).toLocaleDateString()
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
