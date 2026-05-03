import { useState, useEffect, useRef } from "react"
import { NavLink, useSearchParams } from "react-router-dom"
import { ArrowUpDown, Download } from "lucide-react"
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
import { Button } from "@/components/ui/button"
import { useAdminStalledContacts, useExportStalledContacts } from "@/hooks/useInsights"
import { cn, formatLocalDate } from "@/lib/utils"
import type { DateRange } from "@/lib/date-presets"
import { dateRangeToParams } from "@/lib/date-presets"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import { parseISO, isValid, format } from "date-fns"

const PAGE_SIZE = 50

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never"
  return formatLocalDate(dateStr)
}

export default function StalledContacts() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Pagination synced to URL so refresh / back-button preserves position.
  const parsePageIndex = (params: URLSearchParams): number => {
    const raw = parseInt(params.get("page") ?? "1", 10)
    return Number.isFinite(raw) && raw > 0 ? raw - 1 : 0
  }
  const pageIndex = parsePageIndex(searchParams)
  // Read `prev` (the live URL state) inside the updater rather than the
  // closure-captured `pageIndex` so functional updates like `p => p + 1`
  // see the latest value, not a stale render snapshot.
  const setPageIndex = (next: number | ((prev: number) => number)) => {
    setSearchParams(
      (prev) => {
        const value = typeof next === "function" ? next(parsePageIndex(prev)) : next
        const params = new URLSearchParams(prev)
        if (value <= 0) {
          params.delete("page")
        } else {
          params.set("page", String(value + 1))
        }
        return params
      },
      { replace: true },
    )
  }

  const [sortBy, setSortBy] = useState<"days_stalled" | "full_name" | "owner_name">("days_stalled")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [dateRange, setDateRange] = useState<DateRange | null>(() => {
    // Read and validate URL params on mount
    const dateFrom = searchParams.get('date_from')
    const dateTo = searchParams.get('date_to')

    if (dateFrom && dateTo) {
      const fromDate = parseISO(dateFrom)
      const toDate = parseISO(dateTo)

      // Validate both dates are valid and from is before to
      if (isValid(fromDate) && isValid(toDate) && fromDate <= toDate) {
        return { from: fromDate, to: toDate }
      }
      // Invalid dates: clear params
    }

    return null
  })

  const dateParams = dateRangeToParams(dateRange)
  const offset = pageIndex * PAGE_SIZE

  const { data, isLoading, error, isFetching } = useAdminStalledContacts({
    limit: PAGE_SIZE,
    offset,
    sort_by: sortBy,
    sort_dir: sortDir,
    ...dateParams,
  })

  const exportMutation = useExportStalledContacts()

  // Reset pagination when date range changes — but NOT on the initial mount,
  // otherwise visiting a direct URL like ?page=3 gets wiped before the user
  // sees it.
  const didMountRef = useRef(false)
  useEffect(() => {
    if (!didMountRef.current) {
      didMountRef.current = true
      return
    }
    setPageIndex(0)
    // setPageIndex is recreated each render; intentionally not in deps so
    // this effect only fires on dateRange changes, not on every setter identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange])

  const pageCount = Math.ceil((data?.total_count || 0) / PAGE_SIZE)

  const handleSortChange = (column: "days_stalled" | "full_name" | "owner_name") => {
    if (sortBy === column) {
      // Toggle direction if same column
      setSortDir(sortDir === "asc" ? "desc" : "asc")
    } else {
      // New column: set column and reset to desc
      setSortBy(column)
      setSortDir("desc")
    }
    // Always reset to page 1 on sort change
    setPageIndex(0)
  }

  const handleDateRangeChange = (newRange: DateRange | null) => {
    setDateRange(newRange)

    // Sync URL params
    if (newRange?.from && newRange?.to) {
      setSearchParams({
        date_from: format(newRange.from, 'yyyy-MM-dd'),
        date_to: format(newRange.to, 'yyyy-MM-dd'),
      })
    } else {
      setSearchParams({}) // Clear params
    }
  }

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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Stalled Contacts</h1>
              <p className="text-muted-foreground mt-1">
                {data.total_count} contacts with no activity in 14+ days
              </p>
            </div>
            <div className="flex items-center gap-2">
              <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />
              <Button
                variant="outline"
                onClick={() => exportMutation.mutate({ ...dateParams, sort_by: sortBy, sort_dir: sortDir })}
                disabled={exportMutation.isPending}
              >
                <Download className="h-4 w-4 mr-2" />
                {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
              </Button>
            </div>
          </div>

          {/* Table */}
          <Card>
            <CardHeader>
              <CardTitle>Stalled Contact List</CardTitle>
            </CardHeader>
            <CardContent>
              {data.stalled_contacts.length > 0 ? (
                <>
                  <Table aria-label="Stalled contacts">
                    <TableHeader>
                      <TableRow>
                        <TableHead>
                          <button
                            className="flex items-center gap-1 hover:text-foreground cursor-pointer"
                            onClick={() => handleSortChange("full_name")}
                          >
                            Contact Name
                            <ArrowUpDown className="h-4 w-4" />
                          </button>
                        </TableHead>
                        <TableHead>
                          <button
                            className="flex items-center gap-1 hover:text-foreground cursor-pointer"
                            onClick={() => handleSortChange("owner_name")}
                          >
                            Owner
                            <ArrowUpDown className="h-4 w-4" />
                          </button>
                        </TableHead>
                        <TableHead>Last Activity</TableHead>
                        <TableHead>
                          <button
                            className="flex items-center gap-1 hover:text-foreground cursor-pointer"
                            onClick={() => handleSortChange("days_stalled")}
                          >
                            Days Stalled
                            <ArrowUpDown className="h-4 w-4" />
                          </button>
                        </TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className={cn("", isFetching && "opacity-50 pointer-events-none")}>
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

                  {/* Pagination Controls */}
                  <div className="flex justify-between items-center mt-4">
                    <div className="text-sm text-muted-foreground">
                      Showing {offset + 1}-{Math.min(offset + PAGE_SIZE, data.total_count)} of {data.total_count} contacts
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPageIndex(pageIndex - 1)}
                        disabled={pageIndex === 0 || isFetching}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPageIndex(pageIndex + 1)}
                        disabled={pageIndex >= pageCount - 1 || isFetching}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
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
