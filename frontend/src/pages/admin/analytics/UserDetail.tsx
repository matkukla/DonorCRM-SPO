import { useParams, NavLink, Link } from "react-router-dom"
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { useAdminUserPerformance, useAdminUserTrends, useAdminUserJournals } from "@/hooks/useInsights"
import { cn, formatLocalDate } from "@/lib/utils"

const trendConfig = {
  decisions_logged: { label: "Decisions", color: "hsl(var(--chart-1))" },
  donations_received: { label: "Donations", color: "hsl(var(--chart-2))" },
  stage_progressions: { label: "Stage Changes", color: "hsl(var(--chart-3))" },
} satisfies ChartConfig

export default function UserDetail() {
  const { id } = useParams<{ id: string }>()

  // Early check for missing ID
  if (!id) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            {/* Admin Sub-Navigation */}
            <AdminNav />

            <div>
              <p className="text-destructive">User not found</p>
              <Link to="/admin/analytics/dashboard" className="text-primary underline mt-2 inline-block">
                Back to Dashboard
              </Link>
            </div>
          </div>
        </Container>
      </Section>
    )
  }

  // Independent data fetching for each section
  const { data: performanceData, isLoading: performanceLoading, error: performanceError } = useAdminUserPerformance()
  const { data: trendsData, isLoading: trendsLoading } = useAdminUserTrends(id)
  const { data: journalsData, isLoading: journalsLoading } = useAdminUserJournals(id)

  if (performanceLoading) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <AdminNav />
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  if (performanceError) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <AdminNav />
            <p className="text-destructive">Failed to load user performance data. Please try again.</p>
          </div>
        </Container>
      </Section>
    )
  }

  if (!performanceData) return null

  // Find the specific user by ID
  const user = performanceData.users.find((u) => u.id === id)

  if (!user) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <AdminNav />
            <div>
              <p className="text-destructive">User not found</p>
              <Link to="/admin/analytics/dashboard" className="text-primary underline mt-2 inline-block">
                Back to Dashboard
              </Link>
            </div>
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Admin Sub-Navigation */}
          <AdminNav />

          {/* Back Link */}
          <Link to="/admin/analytics/dashboard" className="text-sm text-primary hover:underline">
            ← Back to Dashboard
          </Link>

          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">{user.name}</h1>
            <div className="flex items-center gap-3 mt-2">
              <p className="text-muted-foreground">{user.email}</p>
              <Badge variant="secondary">{user.role}</Badge>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Contacts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{user.total_contacts}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active Journals
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{user.active_journals}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Decisions Logged
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{user.decisions_logged}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Conversion Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{user.conversion_rate.toFixed(1)}%</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Donations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(user.total_donations / 100).toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD'
                  })}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Donation Count
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{user.donation_count}</div>
              </CardContent>
            </Card>
          </div>

          {/* Trend Chart */}
          {trendsLoading ? (
            <Card>
              <CardHeader>
                <CardTitle>{user.name}'s Activity (12 Weeks)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="min-h-[300px] bg-muted rounded animate-pulse" />
              </CardContent>
            </Card>
          ) : !trendsData?.trends.length ? (
            <Card>
              <CardHeader>
                <CardTitle>{user.name}'s Activity (12 Weeks)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="min-h-[300px] flex items-center justify-center">
                  <p className="text-muted-foreground">No trend data available</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>{user.name}'s Activity (12 Weeks)</CardTitle>
                <CardDescription>Decisions, donations, and stage progressions</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={trendConfig} className="min-h-[300px] w-full">
                  <LineChart data={trendsData.trends}>
                    <CartesianGrid vertical={false} />
                    <XAxis
                      dataKey="week_label"
                      tickLine={false}
                      tickMargin={10}
                      axisLine={false}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis tickLine={false} axisLine={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Line
                      dataKey="decisions_logged"
                      stroke="var(--color-decisions_logged)"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                    <Line
                      dataKey="donations_received"
                      stroke="var(--color-donations_received)"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                    <Line
                      dataKey="stage_progressions"
                      stroke="var(--color-stage_progressions)"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ChartContainer>
              </CardContent>
            </Card>
          )}

          {/* Journals List */}
          {journalsLoading ? (
            <Card>
              <CardHeader>
                <CardTitle>Journals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-32 bg-muted rounded animate-pulse" />
              </CardContent>
            </Card>
          ) : !journalsData?.journals.length ? (
            <Card>
              <CardHeader>
                <CardTitle>Journals</CardTitle>
                <CardDescription>0 active journals</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">No journals found</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Journals</CardTitle>
                <CardDescription>{journalsData.journals.length} active journals</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Journal Name</TableHead>
                      <TableHead>Members</TableHead>
                      <TableHead>Decisions</TableHead>
                      <TableHead>Active Members</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {journalsData.journals.map((journal) => (
                      <TableRow key={journal.id}>
                        <TableCell className="font-medium">{journal.name}</TableCell>
                        <TableCell>{journal.member_count}</TableCell>
                        <TableCell>{journal.decision_count}</TableCell>
                        <TableCell>
                          {journal.member_count === 0
                            ? "0 members"
                            : `${journal.active_member_count}/${journal.member_count} active`}
                        </TableCell>
                        <TableCell>
                          {formatLocalDate(journal.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </div>
      </Container>
    </Section>
  )
}

function AdminNav() {
  return (
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
  )
}
