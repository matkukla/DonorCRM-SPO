import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useGifts } from "@/hooks/useGifts"
import { useFilterParams, giftFilterParsers } from "@/hooks/useFilterParams"
import { giftPresets } from "@/lib/filter-presets"
import { FilterBar } from "@/components/shared/FilterBar"
import { useAuth } from "@/providers/AuthProvider"
import { useUsers } from "@/hooks/useUsers"
import { useFunds } from "@/hooks/useImports"
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
import { Plus, Search, Filter } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Gift } from "@/api/gifts"
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
  const isAdmin = user?.role === "admin"

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

  // Fetch funds for fund filter and users for admin owner filter
  const { data: fundsData } = useFunds()
  const { data: usersData } = useUsers()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ search: searchInput || null, page: 1 })
  }

  const handlePageChange = (newPage: number) => {
    setFilters({ page: newPage + 1 })
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
      cell: ({ row }) => (
        <span className="font-semibold">{formatCurrency(row.original.amount_dollars)}</span>
      ),
    },
    {
      accessorKey: "gift_date",
      header: "Date",
      cell: ({ row }) => formatLocalDate(row.original.gift_date),
    },
    {
      accessorKey: "fund_name",
      header: "Fund",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.fund_name || "\u2014"}
        </span>
      ),
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => {
        const desc = row.original.description || ""
        return (
          <span className="text-muted-foreground" title={desc}>
            {desc.length > 40 ? desc.slice(0, 40) + "\u2026" : desc || "\u2014"}
          </span>
        )
      },
    },
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
            <Button onClick={() => navigate("/donations/new")}>
              <Plus className="h-4 w-4 mr-2" />
              Record Donation
            </Button>
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
              fund: "Fund",
              owner: "Owner",
              donor_contact: "Donor",
            }}
            filterValueLabels={{
              ...(usersData ? { owner: Object.fromEntries(usersData.map((u) => [String(u.id), u.full_name])) } : {}),
            }}
            presets={giftPresets}
            onApplyPreset={(preset) => setFilters({ ...preset.getParams(), page: 1 })}
            exportUrl="/donations/export/csv/"
            exportParams={toQueryParams()}
          >
            {/* Search input */}
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

            {/* Date range */}
            <Input
              type="date"
              placeholder="From date"
              value={filters.gift_date_after || ""}
              onChange={(e) => setFilters({ gift_date_after: e.target.value || null, page: 1 })}
              className="w-[150px]"
            />
            <Input
              type="date"
              placeholder="To date"
              value={filters.gift_date_before || ""}
              onChange={(e) => setFilters({ gift_date_before: e.target.value || null, page: 1 })}
              className="w-[150px]"
            />

            {/* Amount range */}
            <Input
              type="number"
              placeholder="Min $"
              value={filters.min_amount || ""}
              onChange={(e) => setFilters({ min_amount: e.target.value || null, page: 1 })}
              className="w-[100px]"
            />
            <Input
              type="number"
              placeholder="Max $"
              value={filters.max_amount || ""}
              onChange={(e) => setFilters({ max_amount: e.target.value || null, page: 1 })}
              className="w-[100px]"
            />

            {/* Fund dropdown */}
            {fundsData && fundsData.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {filters.fund
                      ? fundsData.find((f) => f.id === filters.fund)?.name || "Fund"
                      : "All Funds"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ fund: null, page: 1 })}>
                    All Funds
                  </DropdownMenuItem>
                  {fundsData.map((f) => (
                    <DropdownMenuItem key={f.id} onClick={() => setFilters({ fund: f.id, page: 1 })}>
                      {f.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {/* Admin owner dropdown */}
            {isAdmin && usersData && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {filters.owner
                      ? usersData.find((u) => String(u.id) === filters.owner)?.full_name || "Owner"
                      : "All Owners"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ owner: null, page: 1 })}>
                    All Owners
                  </DropdownMenuItem>
                  {usersData.map((u) => (
                    <DropdownMenuItem key={u.id} onClick={() => setFilters({ owner: String(u.id), page: 1 })}>
                      {u.full_name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
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
            aria-label="Gifts"
          />

          {/* Slide-in detail panel */}
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
