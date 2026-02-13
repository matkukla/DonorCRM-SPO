import { useState } from "react"
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
import { Badge } from "@/components/ui/badge"
import { useAdminStalledContacts } from "@/hooks/useInsights"
import type { StalledContactsParams } from "@/api/insights"
import { cn } from "@/lib/utils"

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never"
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export default function StalledContacts() {
  const [params] = useState<StalledContactsParams>({
    limit: 50,
    offset: 0,
    sort_by: "days_stalled",
    sort_dir: "desc",
  })

  const { data, isLoading, error } = useAdminStalledContacts(params)

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

            <p className="text-destructive">Failed to load stalled contacts. Please try again.</p>
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
            <h1 className="text-3xl font-semibold tracking-tight">Stalled Contacts</h1>
            <p className="text-muted-foreground mt-1">
              {data.total_count} contacts with no activity in 14+ days
            </p>
          </div>

          {/* Table */}
          <Card>
            <CardHeader>
              <CardTitle>Stalled Contact List</CardTitle>
            </CardHeader>
            <CardContent>
              {data.stalled_contacts.length > 0 ? (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Contact Name</TableHead>
                        <TableHead>Owner</TableHead>
                        <TableHead>Last Activity</TableHead>
                        <TableHead>Days Stalled</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.stalled_contacts.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-medium">{item.full_name}</TableCell>
                          <TableCell>{item.owner_name}</TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDate(item.last_activity_date)}
                          </TableCell>
                          <TableCell>
                            {item.days_stalled !== null ? (
                              <Badge
                                variant={
                                  item.days_stalled > 30
                                    ? "destructive"
                                    : item.days_stalled > 14
                                    ? "warning"
                                    : "secondary"
                                }
                              >
                                {item.days_stalled} days
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground">N/A</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{item.status}</Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <p className="text-sm text-muted-foreground mt-4">
                    Showing {data.stalled_contacts.length} of {data.total_count} contacts
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground text-center py-8">No stalled contacts found</p>
              )}
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
