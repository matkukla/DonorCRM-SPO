import { useNavigate, useSearchParams } from "react-router-dom"
import { MessageSquare } from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"

import { useFeedbackEntries } from "@/hooks/useFeedback"
import type { FeedbackEntry, FeedbackStatus, FeedbackType } from "@/api/feedback"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { formatLocalDate } from "@/lib/utils"

const PAGE_SIZE = 25
const ALL = "__all__"

const TYPE_LABELS: Record<FeedbackType, string> = {
  bug: "Bug",
  feature: "Feature Request",
  other: "Other",
}

const STATUS_LABELS: Record<FeedbackStatus, string> = {
  new: "New",
  triaged: "Triaged",
  resolved: "Resolved",
  duplicate: "Duplicate",
}

const TYPE_VARIANTS: Record<
  FeedbackType,
  "default" | "secondary" | "success" | "warning" | "info" | "destructive"
> = {
  bug: "destructive",
  feature: "info",
  other: "secondary",
}

const STATUS_VARIANTS: Record<
  FeedbackStatus,
  "default" | "secondary" | "success" | "warning" | "info" | "destructive"
> = {
  new: "warning",
  triaged: "info",
  resolved: "success",
  duplicate: "secondary",
}

const columns: ColumnDef<FeedbackEntry>[] = [
  {
    accessorKey: "created_at",
    header: "Submitted",
    cell: ({ row }) => (
      <span className="text-muted-foreground tabular-nums">
        {formatLocalDate(row.original.created_at)}
      </span>
    ),
  },
  {
    accessorKey: "type",
    header: "Type",
    cell: ({ row }) => (
      <Badge variant={TYPE_VARIANTS[row.original.type]}>
        {TYPE_LABELS[row.original.type]}
      </Badge>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={STATUS_VARIANTS[row.original.status]}>
        {STATUS_LABELS[row.original.status]}
      </Badge>
    ),
  },
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.title}</span>
    ),
  },
  {
    accessorKey: "submitter_name",
    header: "Submitter",
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="text-sm">{row.original.submitter_name}</span>
        <span className="text-xs text-muted-foreground">
          {row.original.submitter_email}
        </span>
      </div>
    ),
  },
]

export default function AdminFeedback() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const page = parseInt(searchParams.get("page") || "1", 10)
  const typeParam = searchParams.get("type") || ""
  const statusParam = searchParams.get("status") || ""
  const searchParam = searchParams.get("search") || ""

  const queryParams: Record<string, string> = {
    page: String(page),
    page_size: String(PAGE_SIZE),
  }
  if (typeParam) queryParams.type = typeParam
  if (statusParam) queryParams.status = statusParam
  if (searchParam) queryParams.search = searchParam

  const { data, isLoading } = useFeedbackEntries(queryParams)
  const pageCount = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1

  const updateParams = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "") {
        next.delete(key)
      } else {
        next.set(key, value)
      }
    }
    // Reset pagination on any filter change
    if (Object.keys(updates).some((key) => key !== "page")) {
      next.set("page", "1")
    }
    setSearchParams(next)
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div>
            <div className="flex items-center gap-3">
              <MessageSquare className="h-7 w-7 text-muted-foreground" />
              <h1 className="text-3xl font-semibold tracking-tight">Feedback</h1>
            </div>
            <p className="text-muted-foreground mt-1">
              Review and triage feedback submitted by users.
            </p>
          </div>

          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <Input
                placeholder="Search title, description, or submitter..."
                value={searchParam}
                onChange={(event) =>
                  updateParams({ search: event.target.value || null })
                }
              />
            </div>
            <div className="w-[180px]">
              <Select
                value={typeParam || ALL}
                onValueChange={(value) =>
                  updateParams({ type: value === ALL ? null : value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All types</SelectItem>
                  <SelectItem value="bug">Bug</SelectItem>
                  <SelectItem value="feature">Feature Request</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-[180px]">
              <Select
                value={statusParam || ALL}
                onValueChange={(value) =>
                  updateParams({ status: value === ALL ? null : value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All statuses</SelectItem>
                  <SelectItem value="new">New</SelectItem>
                  <SelectItem value="triaged">Triaged</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="duplicate">Duplicate</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DataTable
            columns={columns}
            data={data?.results || []}
            isLoading={isLoading}
            pageCount={pageCount}
            pageIndex={page - 1}
            pageSize={PAGE_SIZE}
            totalCount={data?.count}
            onPageChange={(newPage) =>
              updateParams({ page: String(newPage + 1) })
            }
            onRowClick={(entry) => navigate(`/admin/feedback/${entry.id}`)}
            aria-label="Feedback entries"
          />
        </div>
      </Container>
    </Section>
  )
}
