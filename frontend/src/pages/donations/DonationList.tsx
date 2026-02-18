import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useDonations, useMarkDonationThanked } from "@/hooks/useDonations"
import { useFilterParams, donationFilterParsers } from "@/hooks/useFilterParams"
import { donationPresets } from "@/lib/filter-presets"
import { FilterBar } from "@/components/shared/FilterBar"
import { useAuth } from "@/providers/AuthProvider"
import { useUsers } from "@/hooks/useUsers"
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
import { Plus, Search, Filter, MoreHorizontal, Check, Calendar } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Donation, DonationType, PaymentMethod } from "@/api/donations"
import { donationTypeLabels, paymentMethodLabels } from "@/api/donations"
import { formatLocalDate } from "@/lib/utils"

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
  } = useFilterParams(donationFilterParsers)

  const [searchInput, setSearchInput] = useState(filters.search || "")

  // Sync search input when URL changes externally (e.g., browser back/forward)
  useEffect(() => {
    setSearchInput(filters.search || "")
  }, [filters.search])

  const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
  const { data, isLoading } = useDonations(queryParams)

  const markThankedMutation = useMarkDonationThanked()

  // Fetch users for admin owner filter
  const { data: usersData } = useUsers()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ search: searchInput || null, page: 1 })
  }

  const handlePageChange = (newPage: number) => {
    setFilters({ page: newPage + 1 })
  }

  const columns: ColumnDef<Donation>[] = [
    {
      accessorKey: "date",
      header: "Date",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          {formatLocalDate(row.original.date)}
        </div>
      ),
    },
    {
      accessorKey: "contact_name",
      header: "Donor",
      cell: ({ row }) => (
        <Link
          to={`/contacts/${row.original.contact}`}
          className="font-medium text-primary hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {row.original.contact_name}
        </Link>
      ),
    },
    {
      accessorKey: "amount",
      header: "Amount",
      cell: ({ row }) => (
        <span className="font-semibold">{formatCurrency(row.original.amount)}</span>
      ),
    },
    {
      accessorKey: "donation_type",
      header: "Type",
      cell: ({ row }) => (
        <Badge variant="secondary">
          {donationTypeLabels[row.original.donation_type]}
        </Badge>
      ),
    },
    {
      accessorKey: "payment_method",
      header: "Payment",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {paymentMethodLabels[row.original.payment_method]}
        </span>
      ),
    },
    {
      accessorKey: "thanked",
      header: "Status",
      cell: ({ row }) => (
        row.original.thanked ? (
          <Badge variant="success" className="gap-1">
            <Check className="h-3 w-3" />
            Thanked
          </Badge>
        ) : (
          <Badge variant="warning">Pending</Badge>
        )
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/donations/${row.original.id}`)
              }}
            >
              View details
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/donations/${row.original.id}/edit`)
              }}
            >
              Edit
            </DropdownMenuItem>
            {!row.original.thanked && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  markThankedMutation.mutate(row.original.id)
                }}
              >
                Mark as thanked
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
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
              donation_type: "Type",
              payment_method: "Payment",
              thanked: "Status",
              date_after: "From",
              date_before: "To",
              amount_min: "Min Amount",
              amount_max: "Max Amount",
              fund: "Fund",
              owner: "Owner",
            }}
            filterValueLabels={{
              donation_type: donationTypeLabels,
              payment_method: paymentMethodLabels,
            }}
            presets={donationPresets}
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

            {/* Type dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="sm" className="gap-2">
                  <Filter className="h-4 w-4" />
                  {filters.donation_type ? donationTypeLabels[filters.donation_type as DonationType] || filters.donation_type : "All Types"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setFilters({ donation_type: null, page: 1 })}>
                  All Types
                </DropdownMenuItem>
                {(Object.keys(donationTypeLabels) as DonationType[]).map((t) => (
                  <DropdownMenuItem key={t} onClick={() => setFilters({ donation_type: t, page: 1 })}>
                    {donationTypeLabels[t]}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Payment method dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="sm" className="gap-2">
                  <Filter className="h-4 w-4" />
                  {filters.payment_method ? paymentMethodLabels[filters.payment_method as PaymentMethod] || filters.payment_method : "All Payments"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setFilters({ payment_method: null, page: 1 })}>
                  All Payments
                </DropdownMenuItem>
                {(Object.keys(paymentMethodLabels) as PaymentMethod[]).map((m) => (
                  <DropdownMenuItem key={m} onClick={() => setFilters({ payment_method: m, page: 1 })}>
                    {paymentMethodLabels[m]}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Thanked dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="sm" className="gap-2">
                  <Check className="h-4 w-4" />
                  {filters.thanked === true ? "Thanked" : filters.thanked === false ? "Pending" : "All Status"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setFilters({ thanked: null, page: 1 })}>
                  All Status
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilters({ thanked: true, page: 1 })}>
                  Thanked
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilters({ thanked: false, page: 1 })}>
                  Pending Thank You
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Date range */}
            <Input
              type="date"
              placeholder="From date"
              value={filters.date_after || ""}
              onChange={(e) => setFilters({ date_after: e.target.value || null, page: 1 })}
              className="w-[150px]"
            />
            <Input
              type="date"
              placeholder="To date"
              value={filters.date_before || ""}
              onChange={(e) => setFilters({ date_before: e.target.value || null, page: 1 })}
              className="w-[150px]"
            />

            {/* Amount range */}
            <Input
              type="number"
              placeholder="Min $"
              value={filters.amount_min || ""}
              onChange={(e) => setFilters({ amount_min: e.target.value || null, page: 1 })}
              className="w-[100px]"
            />
            <Input
              type="number"
              placeholder="Max $"
              value={filters.amount_max || ""}
              onChange={(e) => setFilters({ amount_max: e.target.value || null, page: 1 })}
              className="w-[100px]"
            />

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
            onRowClick={(donation) => navigate(`/donations/${donation.id}`)}
          />
        </div>
      </Container>
    </Section>
  )
}
