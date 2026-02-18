import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { usePledges, usePausePledge, useResumePledge, useCancelPledge } from "@/hooks/usePledges"
import { useFilterParams, pledgeFilterParsers } from "@/hooks/useFilterParams"
import { pledgePresets } from "@/lib/filter-presets"
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Plus, Search, Filter, MoreHorizontal, AlertTriangle, Pause, Play, XCircle } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Pledge, PledgeStatus, PledgeFrequency } from "@/api/pledges"
import { pledgeFrequencyLabels, pledgeStatusLabels } from "@/api/pledges"
import { formatLocalDate } from "@/lib/utils"

const PAGE_SIZE = 20

const statusVariants: Record<PledgeStatus, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  active: "success",
  paused: "warning",
  completed: "secondary",
  cancelled: "destructive",
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

  const {
    filters,
    setFilters,
    clearAll,
    activeFilters,
    toQueryParams,
  } = useFilterParams(pledgeFilterParsers)

  const [searchInput, setSearchInput] = useState(filters.search || "")

  // Sync search input when URL changes externally (e.g., browser back/forward)
  useEffect(() => {
    setSearchInput(filters.search || "")
  }, [filters.search])

  const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
  const { data, isLoading } = usePledges(queryParams)

  const pauseMutation = usePausePledge()
  const resumeMutation = useResumePledge()
  const cancelMutation = useCancelPledge()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ search: searchInput || null, page: 1 })
  }

  const handlePageChange = (newPage: number) => {
    setFilters({ page: newPage + 1 })
  }

  const handleCancel = (id: string) => {
    if (window.confirm("Are you sure you want to cancel this pledge?")) {
      cancelMutation.mutate(id)
    }
  }

  const columns: ColumnDef<Pledge>[] = [
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
        <div>
          <span className="font-semibold">{formatCurrency(row.original.amount)}</span>
          <span className="text-muted-foreground">
            {" / "}{pledgeFrequencyLabels[row.original.frequency].toLowerCase()}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "monthly_equivalent",
      header: "Monthly",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {formatCurrency(row.original.monthly_equivalent)}/mo
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Badge variant={statusVariants[row.original.status]}>
            {pledgeStatusLabels[row.original.status]}
          </Badge>
          {row.original.is_late && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              {row.original.days_late}d late
            </Badge>
          )}
        </div>
      ),
    },
    {
      accessorKey: "next_expected_date",
      header: "Next Expected",
      cell: ({ row }) => formatLocalDate(row.original.next_expected_date),
    },
    {
      accessorKey: "fulfillment_percentage",
      header: "Fulfilled",
      cell: ({ row }) => (
        <div className="w-20">
          <div className="flex justify-between text-sm mb-1">
            <span>{Math.round(row.original.fulfillment_percentage)}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full"
              style={{ width: `${Math.min(100, row.original.fulfillment_percentage)}%` }}
            />
          </div>
        </div>
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
                navigate(`/pledges/${row.original.id}`)
              }}
            >
              View details
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/pledges/${row.original.id}/edit`)
              }}
            >
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {row.original.status === "active" && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  pauseMutation.mutate(row.original.id)
                }}
              >
                <Pause className="h-4 w-4 mr-2" />
                Pause
              </DropdownMenuItem>
            )}
            {row.original.status === "paused" && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  resumeMutation.mutate(row.original.id)
                }}
              >
                <Play className="h-4 w-4 mr-2" />
                Resume
              </DropdownMenuItem>
            )}
            {(row.original.status === "active" || row.original.status === "paused") && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  handleCancel(row.original.id)
                }}
                className="text-destructive"
              >
                <XCircle className="h-4 w-4 mr-2" />
                Cancel
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
              <h1 className="text-3xl font-semibold tracking-tight">Pledges</h1>
              <p className="text-muted-foreground mt-1">
                Manage recurring giving commitments
              </p>
            </div>
            <Button onClick={() => navigate("/pledges/new")}>
              <Plus className="h-4 w-4 mr-2" />
              Create Pledge
            </Button>
          </div>

          {/* Filters */}
          <FilterBar
            activeFilters={activeFilters}
            onClearAll={clearAll}
            onRemoveFilter={(key) => setFilters({ [key]: null, page: 1 })}
            filterLabels={{
              status: "Status",
              frequency: "Frequency",
              is_late: "Late",
              start_date_after: "Start From",
              start_date_before: "Start To",
              amount_min: "Min Amount",
              amount_max: "Max Amount",
            }}
            filterValueLabels={{
              status: pledgeStatusLabels,
              frequency: pledgeFrequencyLabels,
            }}
            presets={pledgePresets}
            onApplyPreset={(preset) => setFilters({ ...preset.getParams(), page: 1 })}
            exportUrl="/pledges/export/csv/"
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

            {/* Status dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="sm" className="gap-2">
                  <Filter className="h-4 w-4" />
                  {filters.status ? pledgeStatusLabels[filters.status as PledgeStatus] || filters.status : "All Status"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setFilters({ status: null, page: 1 })}>
                  All Status
                </DropdownMenuItem>
                {(Object.keys(pledgeStatusLabels) as PledgeStatus[]).map((s) => (
                  <DropdownMenuItem key={s} onClick={() => setFilters({ status: s, page: 1 })}>
                    {pledgeStatusLabels[s]}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Frequency dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="sm" className="gap-2">
                  <Filter className="h-4 w-4" />
                  {filters.frequency ? pledgeFrequencyLabels[filters.frequency as PledgeFrequency] || filters.frequency : "All Frequencies"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setFilters({ frequency: null, page: 1 })}>
                  All Frequencies
                </DropdownMenuItem>
                {(Object.keys(pledgeFrequencyLabels) as PledgeFrequency[]).map((f) => (
                  <DropdownMenuItem key={f} onClick={() => setFilters({ frequency: f, page: 1 })}>
                    {pledgeFrequencyLabels[f]}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Late toggle button */}
            <Button
              variant={filters.is_late ? "default" : "secondary"}
              size="sm"
              onClick={() => setFilters({
                is_late: filters.is_late ? null : true,
                page: 1,
              })}
              className="gap-2"
            >
              <AlertTriangle className="h-4 w-4" />
              Late Pledges
            </Button>

            {/* Date range */}
            <Input
              type="date"
              placeholder="Start from"
              value={filters.start_date_after || ""}
              onChange={(e) => setFilters({ start_date_after: e.target.value || null, page: 1 })}
              className="w-[150px]"
            />
            <Input
              type="date"
              placeholder="Start to"
              value={filters.start_date_before || ""}
              onChange={(e) => setFilters({ start_date_before: e.target.value || null, page: 1 })}
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
            onRowClick={(pledge) => navigate(`/pledges/${pledge.id}`)}
          />
        </div>
      </Container>
    </Section>
  )
}
