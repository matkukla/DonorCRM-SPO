import { useParams, NavLink, Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAdminUserPerformance } from "@/hooks/useInsights"
import { cn } from "@/lib/utils"

export default function UserDetail() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, error } = useAdminUserPerformance()

  if (isLoading) {
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

            <p className="text-destructive">Failed to load user performance data. Please try again.</p>
          </div>
        </Container>
      </Section>
    )
  }

  if (!data) return null

  // Find the specific user by ID
  const user = data.users.find((u) => u.id === id)

  if (!user) {
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
        </div>
      </Container>
    </Section>
  )
}
