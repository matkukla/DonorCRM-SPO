import { useNavigate, useSearchParams, Link } from "react-router-dom"
import { usePledges, usePausePledge, useResumePledge, useCancelPledge } from "@/hooks/usePledges"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Plus, Filter, MoreHorizontal, AlertTriangle, Pause, Play, XCircle } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Pledge, PledgeStatus } from "@/api/pledges"
import { pledgeFrequencyLabels, pledgeStatusLabels } from "@/api/pledges"

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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export default function PledgeList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const page = parseInt(searchParams.get("page") || "1", 10)
  const status = searchParams.get("status") as PledgeStatus | undefined
  const isLate = searchParams.get("is_late") === "true"

  const { data, isLoading } = usePledges({
    page,
    page_size: PAGE_SIZE,
    status,
    is_late: isLate || undefined,
  })

  const pauseMutation = usePausePledge()
  const resumeMutation = useResumePledge()
  const cancelMutation = useCancelPledge()

  const handleStatusFilter = (newStatus: PledgeStatus | null) => {
    const params = new URLSearchParams(searchParams)
    if (newStatus) {
      params.set("status", newStatus)
    } else {
      params.delete("status")
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  const handleLateFilter = () => {
    const params = new URLSearchParams(searchParams)
    if (isLate) {
      params.delete("is_late")
    } else {
      params.set("is_late", "true")
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("page", String(newPage + 1))
    setSearchParams(params)
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
      cell: ({ row }) => formatDate(row.original.next_expected_date),
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
          <Card className="p-4">
            <div className="flex flex-wrap gap-4">
              {/* Status filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {status ? pledgeStatusLabels[status] : "All Status"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleStatusFilter(null)}>
                    All Status
                  </DropdownMenuItem>
                  {(Object.keys(pledgeStatusLabels) as PledgeStatus[]).map((s) => (
                    <DropdownMenuItem key={s} onClick={() => handleStatusFilter(s)}>
                      {pledgeStatusLabels[s]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Late filter */}
              <Button
                variant={isLate ? "default" : "secondary"}
                onClick={handleLateFilter}
                className="gap-2"
              >
                <AlertTriangle className="h-4 w-4" />
                Late Pledges Only
              </Button>
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
            onRowClick={(pledge) => navigate(`/pledges/${pledge.id}`)}
          />
        </div>
      </Container>
    </Section>
  )
}
