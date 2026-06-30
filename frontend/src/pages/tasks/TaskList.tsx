import { useState } from "react"
import { useNavigate, useSearchParams, Link } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { useViewAs } from "@/providers/ViewAsProvider"
import { useTasks, useCompleteTask, useReopenTask } from "@/hooks/useTasks"
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
import { Input } from "@/components/ui/input"
import {
  Plus,
  Filter,
  MoreHorizontal,
  AlertTriangle,
  CheckCircle,
  Search,
  Phone,
  Mail,
  Heart,
  Users,
  MessageSquare,
  MoreVertical,
  Megaphone,
  ChevronDown,
  RotateCcw,
} from "lucide-react"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { ColumnDef } from "@tanstack/react-table"
import type { Task, TaskStatus, TaskPriority, TaskType } from "@/api/tasks"
import { taskStatusLabels, taskPriorityLabels, taskTypeLabels } from "@/api/tasks"
import { FilterCombobox } from "@/components/shared/FilterCombobox"
import { formatLocalDate } from "@/lib/utils"
import BroadcastTaskDialog from "./BroadcastTaskDialog"

const PAGE_SIZE = 20

// Status options for the active section's filter. "completed" is excluded
// because completed tasks live in their own section below (issue #168).
const ACTIVE_STATUSES: TaskStatus[] = ["pending", "in_progress", "cancelled"]

const statusVariants: Record<TaskStatus, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  pending: "secondary",
  in_progress: "info",
  completed: "success",
  cancelled: "destructive",
}

const priorityVariants: Record<TaskPriority, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  low: "secondary",
  medium: "default",
  high: "warning",
  urgent: "destructive",
}

const typeIcons: Record<TaskType, React.ReactNode> = {
  call: <Phone className="h-4 w-4" />,
  email: <Mail className="h-4 w-4" />,
  thank_you: <Heart className="h-4 w-4" />,
  meeting: <Users className="h-4 w-4" />,
  follow_up: <MessageSquare className="h-4 w-4" />,
  other: <MoreVertical className="h-4 w-4" />,
}

export default function TaskList() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { isViewingAs } = useViewAs()
  const [broadcastDialogOpen, setBroadcastDialogOpen] = useState(false)
  // Completed Tasks section is expanded by default (issue #168).
  const [completedOpen, setCompletedOpen] = useState(true)
  const canBroadcast = (user?.role === "admin" || user?.role === "supervisor") && !isViewingAs
  const canSeeOwner = user?.role === "admin" || user?.role === "supervisor" || user?.role === "coach"
  const ownerOptions = user?.role === "admin"
    ? [] // admin can see all via usersData (not loaded here -- owner column always visible)
    : (user?.role === "supervisor" || user?.role === "coach")
      ? [
          { id: String(user.id), full_name: `${user.first_name} ${user.last_name}` },
          ...(user.supervised_users?.map((u) => ({
            id: String(u.id),
            full_name: `${u.first_name} ${u.last_name}`,
          })) || []),
        ]
      : []
  const [searchParams, setSearchParams] = useSearchParams()

  const page = parseInt(searchParams.get("page") || "1", 10)
  const completedPage = parseInt(searchParams.get("cpage") || "1", 10)
  const status = searchParams.get("status") as TaskStatus | undefined
  const priority = searchParams.get("priority") as TaskPriority | undefined
  const taskType = searchParams.get("task_type") as TaskType | undefined
  const search = searchParams.get("search") || ""
  const ownerFilter = searchParams.get("owner") || undefined
  const ordering = searchParams.get("ordering") || undefined

  // Active section: incomplete tasks only. Shared filters (priority, type,
  // search, owner) apply here. The status filter here is limited to active
  // statuses (see activeStatusLabels) so it can't contradict `completed: false`.
  const { data, isLoading } = useTasks({
    page,
    page_size: PAGE_SIZE,
    completed: false,
    status,
    priority,
    task_type: taskType,
    search: search || undefined,
    owner: ownerFilter,
    ordering,
  })

  // Completed section (issue #168): completed tasks only, most-recently-completed
  // first. Shares the priority/type/search/owner filters so the two sections stay
  // consistent, but is paginated independently via the `cpage` URL param.
  const { data: completedData, isLoading: isCompletedLoading } = useTasks({
    page: completedPage,
    page_size: PAGE_SIZE,
    completed: true,
    priority,
    task_type: taskType,
    search: search || undefined,
    owner: ownerFilter,
    ordering: "-completed_at",
  })

  const completeMutation = useCompleteTask()
  const reopenMutation = useReopenTask()

  // Shared filters drive both the active and completed sections, so reset both
  // page cursors when they change.
  const resetBothPages = (params: URLSearchParams) => {
    params.set("page", "1")
    params.set("cpage", "1")
  }

  const handleStatusFilter = (newStatus: TaskStatus | null) => {
    const params = new URLSearchParams(searchParams)
    if (newStatus) {
      params.set("status", newStatus)
    } else {
      params.delete("status")
    }
    // Status only narrows the active section; the completed section is unaffected.
    params.set("page", "1")
    setSearchParams(params)
  }

  const handlePriorityFilter = (newPriority: TaskPriority | null) => {
    const params = new URLSearchParams(searchParams)
    if (newPriority) {
      params.set("priority", newPriority)
    } else {
      params.delete("priority")
    }
    resetBothPages(params)
    setSearchParams(params)
  }

  const handleTypeFilter = (newType: TaskType | null) => {
    const params = new URLSearchParams(searchParams)
    if (newType) {
      params.set("task_type", newType)
    } else {
      params.delete("task_type")
    }
    resetBothPages(params)
    setSearchParams(params)
  }

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const searchValue = formData.get("search") as string
    const params = new URLSearchParams(searchParams)
    if (searchValue) {
      params.set("search", searchValue)
    } else {
      params.delete("search")
    }
    resetBothPages(params)
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("page", String(newPage + 1))
    setSearchParams(params)
  }

  const handleCompletedPageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("cpage", String(newPage + 1))
    setSearchParams(params)
  }

  const handleOwnerFilter = (newOwner: string | null) => {
    const params = new URLSearchParams(searchParams)
    if (newOwner) {
      params.set("owner", newOwner)
    } else {
      params.delete("owner")
    }
    resetBothPages(params)
    setSearchParams(params)
  }

  const handleOrderingChange = (newOrdering: string | null) => {
    const params = new URLSearchParams(searchParams)
    if (newOrdering) {
      params.set("ordering", newOrdering)
    } else {
      params.delete("ordering")
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  const handleComplete = (id: string) => {
    completeMutation.mutate(id)
  }

  const handleReopen = (id: string) => {
    reopenMutation.mutate(id)
  }

  const columns: ColumnDef<Task>[] = [
    {
      accessorKey: "title",
      header: "Task",
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 text-muted-foreground">
            {typeIcons[row.original.task_type]}
          </div>
          <div>
            <div className="font-medium">{row.original.title}</div>
            {row.original.broadcast_id ? (
              <div className="flex items-center gap-1 mt-0.5">
                <Megaphone className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">
                  Assigned by {row.original.broadcast_sender_name}
                </span>
              </div>
            ) : row.original.contact_name ? (
              <Link
                to={`/contacts/${row.original.contact}`}
                className="text-sm text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {row.original.contact_name}
              </Link>
            ) : null}
          </div>
        </div>
      ),
    },
    {
      accessorKey: "priority",
      header: "Priority",
      meta: { serverSortKey: "priority" },
      cell: ({ row }) => (
        <Badge variant={priorityVariants[row.original.priority]}>
          {taskPriorityLabels[row.original.priority]}
        </Badge>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Badge variant={statusVariants[row.original.status]}>
            {taskStatusLabels[row.original.status]}
          </Badge>
          {row.original.is_overdue && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              Overdue
            </Badge>
          )}
        </div>
      ),
    },
    {
      accessorKey: "due_date",
      header: "Due Date",
      meta: { serverSortKey: "due_date" },
      cell: ({ row }) => (
        <span className={row.original.is_overdue ? "text-destructive font-medium" : ""}>
          {formatLocalDate(row.original.due_date)}
        </span>
      ),
    },
    ...(canSeeOwner ? [{
      accessorKey: "owner_name" as const,
      header: "Owner",
      cell: ({ row }: { row: { original: Task } }) => (
        <span className="text-muted-foreground">{row.original.owner_name}</span>
      ),
    }] : []),
    {
      id: "actions",
      cell: ({ row }) => {
        const isBroadcast = !!row.original.broadcast_id
        const isOwnItem = String(row.original.owner) === String(user?.id)
        const canEdit = (user?.role === "admin" || isOwnItem) && !(isBroadcast && user?.role === "missionary")
        const canComplete = !isViewingAs && (isOwnItem || user?.role === "admin") && row.original.status !== "completed" && row.original.status !== "cancelled"
        // Reopen mirrors complete's authority: only the owner or an admin, and
        // only for already-completed tasks (issue #176).
        const canReopen = !isViewingAs && (isOwnItem || user?.role === "admin") && row.original.status === "completed"
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Task actions">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/tasks/${row.original.id}`)
                }}
              >
                View details
              </DropdownMenuItem>
              {canEdit && !isViewingAs && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/tasks/${row.original.id}/edit`)
                  }}
                >
                  Edit
                </DropdownMenuItem>
              )}
              {canComplete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation()
                      handleComplete(row.original.id)
                    }}
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Mark Complete
                  </DropdownMenuItem>
                </>
              )}
              {canReopen && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation()
                      handleReopen(row.original.id)
                    }}
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Mark Incomplete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  const pageCount = data ? Math.ceil(data.count / PAGE_SIZE) : 1
  const completedPageCount = completedData ? Math.ceil(completedData.count / PAGE_SIZE) : 1
  const completedCount = completedData?.count ?? 0

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Tasks</h1>
              <p className="text-muted-foreground mt-1">
                Manage your action items and reminders
              </p>
            </div>
            {!isViewingAs && (
              <div className="flex gap-2">
                {canBroadcast && (
                  <Button variant="secondary" onClick={() => setBroadcastDialogOpen(true)}>
                    <Megaphone className="h-4 w-4 mr-2" />
                    Broadcast Task
                  </Button>
                )}
                <Button onClick={() => navigate("/tasks/new")}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Task
                </Button>
              </div>
            )}
          </div>

          {/* Filters */}
          <Card className="p-4">
            <div className="flex flex-wrap gap-4">
              {/* Search */}
              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    name="search"
                    placeholder="Search tasks..."
                    defaultValue={search}
                    className="pl-9 w-64"
                  />
                </div>
                <Button type="submit" variant="secondary">
                  Search
                </Button>
              </form>

              {/* Status filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {status ? taskStatusLabels[status] : "All Status"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleStatusFilter(null)}>
                    All Status
                  </DropdownMenuItem>
                  {ACTIVE_STATUSES.map((s) => (
                    <DropdownMenuItem key={s} onClick={() => handleStatusFilter(s)}>
                      {taskStatusLabels[s]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Priority filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {priority ? taskPriorityLabels[priority] : "All Priority"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handlePriorityFilter(null)}>
                    All Priority
                  </DropdownMenuItem>
                  {(Object.keys(taskPriorityLabels) as TaskPriority[]).map((p) => (
                    <DropdownMenuItem key={p} onClick={() => handlePriorityFilter(p)}>
                      {taskPriorityLabels[p]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Type filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {taskType ? taskTypeLabels[taskType] : "All Types"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleTypeFilter(null)}>
                    All Types
                  </DropdownMenuItem>
                  {(Object.keys(taskTypeLabels) as TaskType[]).map((t) => (
                    <DropdownMenuItem key={t} onClick={() => handleTypeFilter(t)}>
                      {taskTypeLabels[t]}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Owner filter (supervisor) */}
              {canSeeOwner && ownerOptions.length > 0 && (
                <FilterCombobox
                  value={ownerFilter || null}
                  onSelect={(value) => handleOwnerFilter(value)}
                  options={ownerOptions.map((u) => ({ value: u.id, label: u.full_name }))}
                  allLabel="All Owners"
                  searchPlaceholder="Search owners..."
                  size="default"
                />
              )}
            </div>
          </Card>

          {/* Active tasks */}
          <DataTable
            columns={columns}
            data={data?.results || []}
            isLoading={isLoading}
            pageCount={pageCount}
            pageIndex={page - 1}
            pageSize={PAGE_SIZE}
            totalCount={data?.count}
            onPageChange={handlePageChange}
            onRowClick={(task) => navigate(`/tasks/${task.id}`)}
            ordering={ordering}
            onOrderingChange={handleOrderingChange}
            aria-label="Active tasks"
          />

          {/* Completed tasks (issue #168) -- collapsible, paginated independently */}
          <Collapsible open={completedOpen} onOpenChange={setCompletedOpen}>
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center gap-2 text-left text-lg font-semibold tracking-tight hover:text-foreground/80 transition-colors"
                aria-label={`${completedOpen ? "Collapse" : "Expand"} completed tasks`}
              >
                <ChevronDown
                  className={`h-5 w-5 text-muted-foreground transition-transform ${
                    completedOpen ? "" : "-rotate-90"
                  }`}
                />
                Completed Tasks
                <span className="text-sm font-normal text-muted-foreground">
                  ({completedCount})
                </span>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-4">
              <DataTable
                columns={columns}
                data={completedData?.results || []}
                isLoading={isCompletedLoading}
                pageCount={completedPageCount}
                pageIndex={completedPage - 1}
                pageSize={PAGE_SIZE}
                totalCount={completedData?.count}
                onPageChange={handleCompletedPageChange}
                onRowClick={(task) => navigate(`/tasks/${task.id}`)}
                aria-label="Completed tasks"
              />
            </CollapsibleContent>
          </Collapsible>
        </div>

        {canBroadcast && <BroadcastTaskDialog open={broadcastDialogOpen} onOpenChange={setBroadcastDialogOpen} />}
      </Container>
    </Section>
  )
}
