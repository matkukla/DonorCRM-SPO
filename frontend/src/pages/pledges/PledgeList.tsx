import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { useViewAs } from "@/providers/ViewAsProvider"
import { useRecurringGifts } from "@/hooks/useGifts"
import { useFilterParams, recurringGiftFilterParsers } from "@/hooks/useFilterParams"
import { recurringGiftPresets } from "@/lib/filter-presets"
import { FilterBar } from "@/components/shared/FilterBar"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { FilterCombobox } from "@/components/shared/FilterCombobox"
import { Plus, Search, Filter } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { RecurringGift, RecurringGiftStatus, RecurringGiftFrequency } from "@/api/gifts"
import { recurringGiftFrequencyLabels, recurringGiftStatusLabels } from "@/api/gifts"
import { formatLocalDate } from "@/lib/utils"

const PAGE_SIZE = 20

const statusVariants: Record<RecurringGiftStatus, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  active: "success",
  held: "warning",
  completed: "secondary",
  cancelled: "destructive",
  terminated: "destructive",
}

function formatCurrency(amount: string | number): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

export default function PledgeList() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { isViewingAs } = useViewAs()
  const canSeeOwner = user?.role === "admin" || user?.role === "supervisor" || user?.role === "coach"
  const ownerOptions = user?.role === "admin"
    ? [] // admin sees all; no dropdown without usersData
    : (user?.role === "supervisor" || user?.role === "coach")
      ? [
          { id: String(user.id), full_name: `${user.first_name} ${user.last_name}` },
          ...(user.supervised_users?.map((u) => ({
            id: String(u.id),
            full_name: `${u.first_name} ${u.last_name}`,
          })) || []),
        ]
      : []

  const {
    filters,
    setFilters,
    clearAll,
    activeFilters,
    toQueryParams,
  } = useFilterParams(recurringGiftFilterParsers)

  const [searchInput, setSearchInput] = useState(filters.search || "")

  // Sync search input when URL changes externally (e.g., browser back/forward)
  useEffect(() => {
    setSearchInput(filters.search || "")
  }, [filters.search])

  const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
  const { data, isLoading } = useRecurringGifts(queryParams)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ search: searchInput || null, page: 1 })
  }

  const handlePageChange = (newPage: number) => {
    setFilters({ page: newPage + 1 })
  }

  const handleOrderingChange = (ordering: string | null) => {
    setFilters({ ordering: ordering, page: 1 })
  }

  const columns: ColumnDef<RecurringGift>[] = [
    {
      accessorKey: "donor_contact_name",
      header: "Donor Name",
      cell: ({ row }) => (
        <Link
          to={`/contacts/${row.original.donor_contact}`}
          className="font-medium text-primary hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {row.original.donor_contact_name}
        </Link>
      ),
    },
    {
      accessorKey: "amount_dollars",
      header: "Amount",
      meta: { serverSortKey: "amount_cents" },
      cell: ({ row }) => (
        <div>
          <span className="font-semibold">{formatCurrency(row.original.amount_dollars)}</span>
          <span className="text-muted-foreground">
            {" / "}{recurringGiftFrequencyLabels[row.original.frequency].toLowerCase()}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "frequency",
      header: "Frequency",
      meta: { serverSortKey: "frequency" },
      cell: ({ row }) => recurringGiftFrequencyLabels[row.original.frequency],
    },
    {
      accessorKey: "status",
      header: "Status",
      meta: { serverSortKey: "status" },
      cell: ({ row }) => (
        <Badge variant={statusVariants[row.original.status]}>
          {recurringGiftStatusLabels[row.original.status]}
        </Badge>
      ),
    },
    {
      accessorKey: "start_date",
      header: "Start Date",
      meta: { serverSortKey: "start_date" },
      cell: ({ row }) => formatLocalDate(row.original.start_date),
    },
    ...(canSeeOwner ? [{
      accessorKey: "owner_name" as const,
      header: "Owner",
      cell: ({ row }: { row: { original: RecurringGift } }) => (
        <span className="text-muted-foreground">{row.original.owner_name}</span>
      ),
    }] : []),
  ]

  const pageCount = data ? Math.ceil(data.count / PAGE_SIZE) : 1

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Pledges</h1>
              <p className="text-muted-foreground mt-1">
                Manage recurring giving commitments
              </p>
            </div>
            {!isViewingAs && (
              <Button onClick={() => navigate("/pledges/new")}>
                <Plus className="h-4 w-4 mr-2" />
                Create Pledge
              </Button>
            )}
          </div>

          {/* Filters */}
          <FilterBar
            activeFilters={activeFilters}
            onClearAll={clearAll}
            onRemoveFilter={(key) => setFilters({ [key]: null, page: 1 })}
            filterLabels={{
              search: "Search",
              status: "Status",
              frequency: "Frequency",
              owner: "Owner",
            }}
            filterValueLabels={{
              status: recurringGiftStatusLabels,
              frequency: recurringGiftFrequencyLabels,
              ...(ownerOptions.length > 0 ? { owner: Object.fromEntries(ownerOptions.map((u) => [u.id, u.full_name])) } : {}),
            }}
            presets={recurringGiftPresets}
            onApplyPreset={(preset) => setFilters({ ...preset.getParams(), page: 1 })}
            exportUrl="/pledges/recurring/export/csv/"
            exportParams={toQueryParams()}
          >
            {/* Row 1: Search */}
            <div className="flex flex-wrap items-center gap-2 w-full">
              <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-[200px]">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by donor name..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Button type="submit" variant="secondary">
                  Search
                </Button>
              </form>
            </div>

            {/* Row 2: Status + frequency + owner */}
            <div className="flex flex-wrap items-center gap-2 w-full">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {filters.status ? recurringGiftStatusLabels[filters.status as RecurringGiftStatus] || filters.status : "All Status"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ status: null, page: 1 })}>
                    All Status
                  </DropdownMenuItem>
                  {(Object.keys(recurringGiftStatusLabels) as RecurringGiftStatus[]).map((s) => (
                    <DropdownMenuItem key={s} onClick={() => setFilters({ status: s, page: 1 })}>
                      {recurringGiftStatusLabels[s]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {filters.frequency ? recurringGiftFrequencyLabels[filters.frequency as RecurringGiftFrequency] || filters.frequency : "All Frequencies"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ frequency: null, page: 1 })}>
                    All Frequencies
                  </DropdownMenuItem>
                  {(Object.keys(recurringGiftFrequencyLabels) as RecurringGiftFrequency[]).map((f) => (
                    <DropdownMenuItem key={f} onClick={() => setFilters({ frequency: f, page: 1 })}>
                      {recurringGiftFrequencyLabels[f]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              {canSeeOwner && ownerOptions.length > 0 && (
                <FilterCombobox
                  value={filters.owner || null}
                  onSelect={(value) => setFilters({ owner: value, page: 1 })}
                  options={ownerOptions.map((u) => ({ value: u.id, label: u.full_name }))}
                  allLabel="All Owners"
                  searchPlaceholder="Search owners..."
                />
              )}
            </div>
          </FilterBar>

          {/* Data Table */}
          <DataTable
            columns={columns}
            data={data?.results || []}
            isLoading={isLoading}
            pageCount={pageCount}
            pageIndex={filters.page - 1}
            pageSize={PAGE_SIZE}
            totalCount={data?.count}
            onPageChange={handlePageChange}
            onRowClick={(rg) => navigate(`/pledges/${rg.id}`)}
            ordering={filters.ordering}
            onOrderingChange={handleOrderingChange}
            aria-label="Recurring gifts"
          />
        </div>
      </Container>
    </Section>
  )
}
