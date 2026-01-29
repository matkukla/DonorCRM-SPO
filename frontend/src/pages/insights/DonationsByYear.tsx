import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useDonationsByYear } from "@/hooks/useInsights"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export default function DonationsByYear() {
  const { data, isLoading, error } = useDonationsByYear(5)

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Donations by Year</h1>
            <p className="text-muted-foreground mt-1">
              Annual donation summary
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
              {/* Summary Card */}
              <Card>
                <CardHeader>
                  <CardTitle>5-Year Summary</CardTitle>
                  <CardDescription>
                    {data.total_donations} donations totaling {formatCurrency(data.grand_total)}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      <BarChart data={data.years}>
                        <XAxis dataKey="year" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
                        <Tooltip
                          formatter={(value: number) => [formatCurrency(value), "Total"]}
                          labelFormatter={(label) => `Year ${label}`}
                        />
                        <Bar dataKey="total" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Data Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Yearly Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Year</TableHead>
                        <TableHead className="text-right">Donations</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.years.map((year) => (
                        <TableRow key={year.year}>
                          <TableCell className="font-medium">{year.year}</TableCell>
                          <TableCell className="text-right">{year.count}</TableCell>
                          <TableCell className="text-right">{formatCurrency(year.total)}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="bg-muted/50 font-semibold">
                        <TableCell>Total</TableCell>
                        <TableCell className="text-right">{data.total_donations}</TableCell>
                        <TableCell className="text-right">{formatCurrency(data.grand_total)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </Container>
    </Section>
  )
}
