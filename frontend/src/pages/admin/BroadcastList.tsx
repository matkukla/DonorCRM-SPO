import { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useBroadcasts } from "@/hooks/useBroadcasts"
import { broadcastTargetLabels } from "@/api/broadcasts"
import type { BroadcastTask } from "@/api/broadcasts"
import { taskPriorityLabels } from "@/api/tasks"
import type { TaskPriority } from "@/api/tasks"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Megaphone, Plus } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"
import type { ColumnDef } from "@tanstack/react-table"
import BroadcastTaskDialog from "@/pages/tasks/BroadcastTaskDialog"

const PAGE_SIZE = 20

const priorityVariants: Record<TaskPriority, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  low: "secondary",
  medium: "default",
  high: "warning",
  urgent: "destructive",
}

function BroadcastProgress({ completed, total }: { completed: number; total: number }) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium tabular-nums">{completed}/{total}</span>
      <Progress value={pct} className="h-2 w-20" />
    </div>
  )
}

const columns: ColumnDef<BroadcastTask>[] = [
  {
    accessorKey: "title",
    header: "Task",
    cell: ({ row }) => (
      <div>
        <div className="font-medium">{row.original.title}</div>
        <span className="text-xs text-muted-foreground">
          {broadcastTargetLabels[row.original.target_type]}
        </span>
      </div>
    ),
  },
  {
    accessorKey: "sender_name",
    header: "Sent By",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.sender_name}</span>
    ),
  },
  {
    accessorKey: "due_date",
    header: "Due Date",
    cell: ({ row }) => formatLocalDate(row.original.due_date),
  },
  {
    accessorKey: "priority",
    header: "Priority",
    cell: ({ row }) => (
      <Badge variant={priorityVariants[row.original.priority]}>
        {taskPriorityLabels[row.original.priority]}
      </Badge>
    ),
  },
  {
    id: "progress",
    header: "Completion",
    cell: ({ row }) => (
      <BroadcastProgress
        completed={row.original.completed_count}
        total={row.original.total_count}
      />
    ),
  },
  {
    id: "status",
    header: "Status",
    cell: ({ row }) => {
      if (row.original.is_cancelled) {
        return <Badge variant="destructive">Cancelled</Badge>
      }
      if (row.original.completed_count === row.original.total_count && row.original.total_count > 0) {
        return <Badge variant="success">Complete</Badge>
      }
      return <Badge variant="secondary">Active</Badge>
    },
  },
]

export default function BroadcastList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [broadcastDialogOpen, setBroadcastDialogOpen] = useState(false)

  const page = parseInt(searchParams.get("page") || "1", 10)

  const { data, isLoading } = useBroadcasts({ page, page_size: PAGE_SIZE })

  const pageCount = data ? Math.ceil(data.count / PAGE_SIZE) : 1

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("page", String(newPage + 1))
    setSearchParams(params)
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <Megaphone className="h-7 w-7 text-muted-foreground" />
                <h1 className="text-3xl font-semibold tracking-tight">Broadcasts</h1>
              </div>
              <p className="text-muted-foreground mt-1">
                Track broadcast task completion across your organization
              </p>
            </div>
            <Button onClick={() => setBroadcastDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Broadcast Task
            </Button>
          </div>

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
            onRowClick={(broadcast) => navigate(`/broadcasts/${broadcast.id}`)}
            aria-label="Broadcasts"
          />
        </div>

        <BroadcastTaskDialog open={broadcastDialogOpen} onOpenChange={setBroadcastDialogOpen} />
      </Container>
    </Section>
  )
}
