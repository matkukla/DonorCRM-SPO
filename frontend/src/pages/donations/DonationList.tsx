import { useState } from "react"
import { useNavigate, useSearchParams, Link } from "react-router-dom"
import { useDonations, useMarkDonationThanked } from "@/hooks/useDonations"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Plus, Search, Filter, MoreHorizontal, Check, Calendar } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Donation, DonationType } from "@/api/donations"
import { donationTypeLabels, paymentMethodLabels } from "@/api/donations"

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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export default function DonationList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [searchInput, setSearchInput] = useState(searchParams.get("search") || "")

  const page = parseInt(searchParams.get("page") || "1", 10)
  const search = searchParams.get("search") || ""
  const donationType = searchParams.get("donation_type") as DonationType | undefined
  const thanked = searchParams.get("thanked")

  const { data, isLoading } = useDonations({
    page,
    page_size: PAGE_SIZE,
    search,
    donation_type: donationType,
    thanked: thanked === "true" ? true : thanked === "false" ? false : undefined,
  })

  const markThankedMutation = useMarkDonationThanked()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (searchInput) {
      params.set("search", searchInput)
    } else {
      params.delete("search")
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  const handleTypeFilter = (type: DonationType | null) => {
    const params = new URLSearchParams(searchParams)
    if (type) {
      params.set("donation_type", type)
    } else {
      params.delete("donation_type")
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  const handleThankedFilter = (value: "all" | "true" | "false") => {
    const params = new URLSearchParams(searchParams)
    if (value === "all") {
      params.delete("thanked")
    } else {
      params.set("thanked", value)
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("page", String(newPage + 1))
    setSearchParams(params)
  }

  const columns: ColumnDef<Donation>[] = [
    {
      accessorKey: "date",
      header: "Date",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          {formatDate(row.original.date)}
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
          <Card className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <form onSubmit={handleSearch} className="flex-1 flex gap-2">
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

              {/* Type filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {donationType ? donationTypeLabels[donationType] : "All Types"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleTypeFilter(null)}>
                    All Types
                  </DropdownMenuItem>
                  {(Object.keys(donationTypeLabels) as DonationType[]).map((t) => (
                    <DropdownMenuItem key={t} onClick={() => handleTypeFilter(t)}>
                      {donationTypeLabels[t]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Thanked filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" className="gap-2">
                    <Check className="h-4 w-4" />
                    {thanked === "true" ? "Thanked" : thanked === "false" ? "Pending" : "All Status"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleThankedFilter("all")}>
                    All Status
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleThankedFilter("true")}>
                    Thanked
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleThankedFilter("false")}>
                    Pending Thank You
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </Card>

          {/* Data Table */}
          <DataTable
            columns={columns}
            data={data?.results || []}
            isLoading={isLoading}
            pageCount={pageCount}
            pageIndex={page - 1}
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
