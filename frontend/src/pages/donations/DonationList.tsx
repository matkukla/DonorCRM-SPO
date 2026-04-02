import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useViewAs } from "@/providers/ViewAsProvider"
import { useGifts } from "@/hooks/useGifts"
import { useFilterParams, giftFilterParsers } from "@/hooks/useFilterParams"
import { giftPresets } from "@/lib/filter-presets"
import { FilterBar } from "@/components/shared/FilterBar"
import { useAuth } from "@/providers/AuthProvider"
import { useUsers } from "@/hooks/useUsers"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { FilterCombobox } from "@/components/shared/FilterCombobox"
import { Badge } from "@/components/ui/badge"
import { Plus, Search, Filter, Repeat } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Gift } from "@/api/gifts"
import { giftPaymentTypeLabels } from "@/api/gifts"
import { formatLocalDate } from "@/lib/utils"
import { DonationDetailPanel } from "./DonationDetail"

const PAGE_SIZE = 20

function formatCurrency(amount: string | number): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

export default function DonationList() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { isViewingAs } = useViewAs()
  const isAdmin = user?.role === "admin"
  const canSeeOwner = user?.role === "admin" || user?.role === "supervisor" || user?.role === "coach"

  const {
    filters,
    setFilters,
    clearAll,
    activeFilters,
    toQueryParams,
  } = useFilterParams(giftFilterParsers)

  const [searchInput, setSearchInput] = useState(filters.search || "")
  const [selectedGiftId, setSelectedGiftId] = useState<string | null>(null)

  // Sync search input when URL changes externally (e.g., browser back/forward)
  useEffect(() => {
    setSearchInput(filters.search || "")
  }, [filters.search])

  const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
  const { data, isLoading } = useGifts(queryParams)

  // Fetch users for owner filter
  const { data: usersData } = useUsers()
  const ownerOptions = user?.role === "admin"
    ? (usersData || []).map((u) => ({ id: String(u.id), full_name: u.full_name }))
    : (user?.role === "supervisor" || user?.role === "coach")
      ? [
          { id: String(user.id), full_name: `${user.first_name} ${user.last_name}` },
          ...(user.supervised_users?.map((u) => ({
            id: String(u.id),
            full_name: `${u.first_name} ${u.last_name}`,
          })) || []),
        ]
      : []

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

  const columns: ColumnDef<Gift>[] = [
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
        <div className="flex items-center gap-2">
          <span className="font-semibold">{formatCurrency(row.original.amount_dollars)}</span>
          {row.original.is_recurring && (
            <Badge variant="outline" className="gap-1 text-xs font-normal">
              <Repeat className="h-3 w-3" />
              {row.original.recurring_gift_frequency || "Recurring"}
            </Badge>
          )}
        </div>
      ),
    },
    {
      accessorKey: "gift_date",
      header: "Date",
      meta: { serverSortKey: "gift_date" },
      cell: ({ row }) => formatLocalDate(row.original.gift_date),
    },
    {
      accessorKey: "payment_type_display",
      header: "Type",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.payment_type_display || "---"}
        </span>
      ),
    },
    ...(canSeeOwner ? [{
      accessorKey: "owner_name" as const,
      header: "Owner",
      cell: ({ row }: { row: { original: Gift } }) => (
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
              <h1 className="text-3xl font-semibold tracking-tight">Donations</h1>
              <p className="text-muted-foreground mt-1">
                Track and manage donor contributions
              </p>
            </div>
            {!isViewingAs && (
              <Button onClick={() => navigate("/donations/new")}>
                <Plus className="h-4 w-4 mr-2" />
                Record Donation
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
              gift_date_after: "From",
              gift_date_before: "To",
              min_amount: "Min Amount",
              max_amount: "Max Amount",
              payment_type: "Type",
              owner: "Owner",
              donor_contact: "Donor",
              is_recurring: "Donation Type",
            }}
            filterValueLabels={{
              ...(ownerOptions.length > 0 ? { owner: Object.fromEntries(ownerOptions.map((u) => [u.id, u.full_name])) } : {}),
              payment_type: giftPaymentTypeLabels,
              is_recurring: { "true": "Recurring", "false": "One-time" },
            }}
            presets={giftPresets}
            onApplyPreset={(preset) => setFilters({ ...preset.getParams(), page: 1 })}
            exportUrl="/donations/export/csv/"
            exportParams={toQueryParams()}
          >
            {/* Row 1: Search + amount range */}
            <div className="flex flex-wrap items-center gap-3 w-full">
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
              <Input
                type="number"
                placeholder="Min $"
                value={filters.min_amount || ""}
                onChange={(e) => setFilters({ min_amount: e.target.value || null, page: 1 })}
                className="w-[110px]"
              />
              <Input
                type="number"
                placeholder="Max $"
                value={filters.max_amount || ""}
                onChange={(e) => setFilters({ max_amount: e.target.value || null, page: 1 })}
                className="w-[110px]"
              />
            </div>

            {/* Row 2: Date range + type + owner */}
            <div className="flex flex-wrap items-center gap-3 w-full">
              <Input
                type="date"
                placeholder="From date"
                value={filters.gift_date_after || ""}
                onChange={(e) => setFilters({ gift_date_after: e.target.value || null, page: 1 })}
                className="w-[160px]"
              />
              <Input
                type="date"
                placeholder="To date"
                value={filters.gift_date_before || ""}
                onChange={(e) => setFilters({ gift_date_before: e.target.value || null, page: 1 })}
                className="w-[160px]"
              />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {filters.payment_type
                      ? giftPaymentTypeLabels[filters.payment_type] || "Type"
                      : "All Types"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ payment_type: null, page: 1 })}>
                    All Types
                  </DropdownMenuItem>
                  {Object.entries(giftPaymentTypeLabels).map(([value, label]) => (
                    <DropdownMenuItem key={value} onClick={() => setFilters({ payment_type: value, page: 1 })}>
                      {label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Repeat className="h-4 w-4" />
                    {filters.is_recurring === "true"
                      ? "Recurring"
                      : filters.is_recurring === "false"
                        ? "One-time"
                        : "All Donations"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ is_recurring: null, page: 1 })}>
                    All Donations
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setFilters({ is_recurring: "false", page: 1 })}>
                    One-time Only
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setFilters({ is_recurring: "true", page: 1 })}>
                    Recurring Only
                  </DropdownMenuItem>
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
            onRowClick={(gift) => setSelectedGiftId(gift.id)}
            ordering={filters.ordering}
            onOrderingChange={handleOrderingChange}
            aria-label="Gifts"
          />

          {/* Detail panel */}
          <DonationDetailPanel
            open={!!selectedGiftId}
            giftId={selectedGiftId}
            onClose={() => setSelectedGiftId(null)}
          />
        </div>
      </Container>
    </Section>
  )
}
