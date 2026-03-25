import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useBroadcast, useBroadcastCopies, useCancelBroadcast } from "@/hooks/useBroadcasts"
import { broadcastTargetLabels } from "@/api/broadcasts"
import { taskStatusLabels } from "@/api/tasks"
import type { Task, TaskStatus } from "@/api/tasks"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { ArrowLeft, Users, CheckCircle, TrendingUp, AlertTriangle } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"
import { toast } from "sonner"
import type { ColumnDef } from "@tanstack/react-table"

const COPIES_PAGE_SIZE = 20

const statusVariants: Record<TaskStatus, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  pending: "secondary",
  in_progress: "info",
  completed: "success",
  cancelled: "destructive",
}

const copiesColumns: ColumnDef<Task>[] = [
  {
    accessorKey: "owner_name",
    header: "Recipient",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.owner_name}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={statusVariants[row.original.status]}>
        {taskStatusLabels[row.original.status]}
      </Badge>
    ),
  },
  {
    accessorKey: "completed_at",
    header: "Completed",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.completed_at ? formatLocalDate(row.original.completed_at) : "-"}
      </span>
    ),
  },
  {
    accessorKey: "due_date",
    header: "Due Date",
    cell: ({ row }) => formatLocalDate(row.original.due_date),
  },
]

export default function BroadcastDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [copiesPage, setCopiesPage] = useState(1)

  const { data: broadcast, isLoading: broadcastLoading } = useBroadcast(id!)
  const { data: copiesData, isLoading: copiesLoading } = useBroadcastCopies(id!, copiesPage)
  const cancelMutation = useCancelBroadcast()

  const handleCancel = () => {
    if (window.confirm("Cancel this broadcast? Incomplete copies will be removed. Completed copies will remain.")) {
      cancelMutation.mutate(id!, {
        onSuccess: () => toast.success("Broadcast cancelled"),
        onError: () => toast.error("Failed to cancel broadcast"),
      })
    }
  }

  const handleCopiesPageChange = (newPage: number) => {
    setCopiesPage(newPage + 1)
  }

  if (broadcastLoading || !broadcast) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  const pct = broadcast.total_count > 0
    ? Math.round((broadcast.completed_count / broadcast.total_count) * 100)
    : 0

  const copiesPageCount = copiesData ? Math.ceil(copiesData.count / COPIES_PAGE_SIZE) : 1

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Back link */}
          <Button
            variant="ghost"
            className="gap-2 -ml-2"
            onClick={() => navigate("/admin/broadcasts")}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Broadcasts
          </Button>

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">{broadcast.title}</h1>
              <p className="text-muted-foreground mt-1">
                Sent by {broadcast.sender_name} on {formatLocalDate(broadcast.created_at)} to{" "}
                {broadcastTargetLabels[broadcast.target_type]}
              </p>
            </div>
            <div className="flex gap-2">
              {!broadcast.is_cancelled && (
                <Button
                  variant="destructive"
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? "Cancelling..." : "Cancel Broadcast"}
                </Button>
              )}
            </div>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Recipients</p>
                    <p className="text-2xl font-bold">{broadcast.recipient_count}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Completed</p>
                    <p className="text-2xl font-bold">
                      {broadcast.completed_count} / {broadcast.total_count}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Progress</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-2xl font-bold tabular-nums">{pct}%</span>
                      <Progress value={pct} className="h-3 w-24" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Cancelled alert */}
          {broadcast.is_cancelled && broadcast.cancelled_at && (
            <div className="flex items-center gap-3 p-4 rounded-lg border border-destructive/50 bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm">
                This broadcast was cancelled on {formatLocalDate(broadcast.cancelled_at)}.
                Completed copies remain visible to recipients.
              </p>
            </div>
          )}

          {/* Description */}
          {broadcast.description && (
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground mb-1">Description</p>
                <p>{broadcast.description}</p>
              </CardContent>
            </Card>
          )}

          {/* Per-user copy table */}
          <div>
            <h2 className="text-xl font-semibold tracking-tight mb-4">Recipient Status</h2>
            <DataTable
              columns={copiesColumns}
              data={copiesData?.results || []}
              isLoading={copiesLoading}
              pageCount={copiesPageCount}
              pageIndex={copiesPage - 1}
              pageSize={COPIES_PAGE_SIZE}
              totalCount={copiesData?.count}
              onPageChange={handleCopiesPageChange}
              aria-label="Broadcast copies"
            />
          </div>
        </div>
      </Container>
    </Section>
  )
}
