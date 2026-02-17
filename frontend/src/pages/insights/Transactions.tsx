import { Link } from "react-router-dom"
import { useFilterParams, transactionFilterParsers } from "@/hooks/useFilterParams"
import { FilterBar } from "@/components/shared/FilterBar"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useTransactions } from "@/hooks/useInsights"
import { Receipt, ChevronLeft, ChevronRight } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

const donationTypeLabels: Record<string, string> = {
  one_time: "One-Time",
  recurring: "Recurring",
  special: "Special",
}

const paymentMethodLabels: Record<string, string> = {
  check: "Check",
  cash: "Cash",
  credit_card: "Credit Card",
  bank_transfer: "Bank Transfer",
  other: "Other",
}

const PAGE_SIZE = 50

export default function Transactions() {
  const {
    filters,
    setFilters,
    clearAll,
    activeFilters,
  } = useFilterParams(transactionFilterParsers)

  const { data, isLoading, error } = useTransactions({
    limit: PAGE_SIZE,
    offset: filters.offset,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  })

  const totalPages = data ? Math.ceil(data.total_count / PAGE_SIZE) : 0
  const currentPage = Math.floor(filters.offset / PAGE_SIZE) + 1

  const handlePrevPage = () => {
    setFilters({ offset: Math.max(0, filters.offset - PAGE_SIZE) })
  }

  const handleNextPage = () => {
    if (data && filters.offset + PAGE_SIZE < data.total_count) {
      setFilters({ offset: filters.offset + PAGE_SIZE })
    }
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Transactions Ledger</h1>
            <p className="text-muted-foreground mt-1">
              Full donation transaction log
            </p>
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load data. Please try again.
            </div>
          )}

          {/* Filters */}
          <FilterBar
            activeFilters={activeFilters}
            onClearAll={clearAll}
            onRemoveFilter={(key) => setFilters({ [key]: null, offset: 0 })}
            filterLabels={{
              date_from: "From",
              date_to: "To",
            }}
          >
            <div className="flex gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-foreground">From:</label>
                <Input
                  type="date"
                  value={filters.date_from || ""}
                  onChange={(e) => setFilters({
                    date_from: e.target.value || null,
                    offset: 0,
                  })}
                  className="w-[150px]"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-foreground">To:</label>
                <Input
                  type="date"
                  value={filters.date_to || ""}
                  onChange={(e) => setFilters({
                    date_to: e.target.value || null,
                    offset: 0,
                  })}
                  className="w-[150px]"
                />
              </div>
            </div>
          </FilterBar>

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
                    <Receipt className="h-5 w-5 text-muted-foreground" />
                    <CardTitle>Transaction Log</CardTitle>
                  </div>
                  <CardDescription>
                    {data.total_count} total transactions
                  </CardDescription>
                </CardHeader>
              </Card>

              {/* Transactions Table */}
              <Card>
                <CardContent className="pt-6">
                  {data.transactions.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No transactions found.
                    </div>
                  ) : (
                    <>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>Contact</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Method</TableHead>
                            <TableHead className="text-right">Amount</TableHead>
                            <TableHead>Thanked</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {data.transactions.map((tx) => (
                            <TableRow key={tx.id}>
                              <TableCell>{formatLocalDate(tx.date)}</TableCell>
                              <TableCell>
                                <Link
                                  to={`/contacts/${tx.contact_id}`}
                                  className="font-medium hover:underline text-primary"
                                >
                                  {tx.contact_name}
                                </Link>
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline">
                                  {donationTypeLabels[tx.donation_type] || tx.donation_type}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                {paymentMethodLabels[tx.payment_method] || tx.payment_method}
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                {formatCurrency(tx.amount)}
                              </TableCell>
                              <TableCell>
                                {tx.thanked ? (
                                  <Badge variant="secondary">Yes</Badge>
                                ) : (
                                  <Badge variant="outline">No</Badge>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>

                      {/* Pagination */}
                      {totalPages > 1 && (
                        <div className="flex items-center justify-between mt-4 pt-4 border-t">
                          <div className="text-sm text-muted-foreground">
                            Page {currentPage} of {totalPages}
                          </div>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={handlePrevPage}
                              disabled={filters.offset === 0}
                            >
                              <ChevronLeft className="h-4 w-4 mr-1" />
                              Previous
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={handleNextPage}
                              disabled={filters.offset + PAGE_SIZE >= data.total_count}
                            >
                              Next
                              <ChevronRight className="h-4 w-4 ml-1" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </>
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
