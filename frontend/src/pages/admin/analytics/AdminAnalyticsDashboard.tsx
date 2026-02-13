import { NavLink } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useAdminDashboardOverview, useAdminConversionFunnel } from "@/hooks/useInsights"
import { cn } from "@/lib/utils"

export default function AdminAnalyticsDashboard() {
  const { data, isLoading, error } = useAdminDashboardOverview()
  const { data: funnelData, isLoading: funnelLoading } = useAdminConversionFunnel()

  if (isLoading || funnelLoading) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            {/* Admin Sub-Navigation */}
            <div className="flex gap-4 border-b border-border pb-2">
              <NavLink
                to="/admin"
                end
                className={({ isActive }) =>
                  cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Users
              </NavLink>
              <NavLink
                to="/admin/imports"
                className={({ isActive }) =>
                  cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Import Center
              </NavLink>
              <NavLink
                to="/admin/analytics"
                className={({ isActive }) =>
                  cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Analytics
              </NavLink>
            </div>

            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  if (error) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            {/* Admin Sub-Navigation */}
            <div className="flex gap-4 border-b border-border pb-2">
              <NavLink
                to="/admin"
                end
                className={({ isActive }) =>
                  cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Users
              </NavLink>
              <NavLink
                to="/admin/imports"
                className={({ isActive }) =>
                  cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Import Center
              </NavLink>
              <NavLink
                to="/admin/analytics"
                className={({ isActive }) =>
                  cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Analytics
              </NavLink>
            </div>

            <p className="text-destructive">Failed to load dashboard data. Please try again.</p>
          </div>
        </Container>
      </Section>
    )
  }

  if (!data) return null

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Admin Sub-Navigation */}
          <div className="flex gap-4 border-b border-border pb-2">
            <NavLink
              to="/admin"
              end
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Users
            </NavLink>
            <NavLink
              to="/admin/imports"
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Import Center
            </NavLink>
            <NavLink
              to="/admin/analytics"
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Analytics
            </NavLink>
          </div>

          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Analytics Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Organization-wide fundraising analytics
            </p>
          </div>

          {/* Summary Cards Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Contacts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.total_contacts}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active Journals
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.active_journals}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Stalled Contacts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.stalled_contacts}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Conversion Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{data.conversion_rate.toFixed(1)}%</div>
              </CardContent>
            </Card>
          </div>

          {/* Donations Card */}
          <Card>
            <CardHeader>
              <CardTitle>Donations (12 Months)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Amount</p>
                  <p className="text-2xl font-bold">
                    {(data.donations_12m.total_amount / 100).toLocaleString('en-US', {
                      style: 'currency',
                      currency: 'USD'
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Donation Count</p>
                  <p className="text-2xl font-bold">{data.donations_12m.total_count}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Conversion Funnel */}
          {funnelData && (
            <Card>
              <CardHeader>
                <CardTitle>Conversion Funnel</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Stage</TableHead>
                      <TableHead className="text-right">Count</TableHead>
                      <TableHead className="text-right">Percentage</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {funnelData.funnel.map((stage) => (
                      <TableRow key={stage.label}>
                        <TableCell className="font-medium">{stage.label}</TableCell>
                        <TableCell className="text-right">{stage.count}</TableCell>
                        <TableCell className="text-right">{stage.percentage.toFixed(1)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <p className="text-sm text-muted-foreground mt-4">
                  Total contacts in pipeline: {funnelData.total_contacts_in_pipeline}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </Container>
    </Section>
  )
}
