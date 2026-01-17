import { useNavigate, useSearchParams, Link } from "react-router-dom"
import { useTasks, useCompleteTask } from "@/hooks/useTasks"
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
} from "lucide-react"
import type { ColumnDef } from "@tanstack/react-table"
import type { Task, TaskStatus, TaskPriority, TaskType } from "@/api/tasks"
import { taskStatusLabels, taskPriorityLabels, taskTypeLabels } from "@/api/tasks"

const PAGE_SIZE = 20

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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export default function TaskList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const page = parseInt(searchParams.get("page") || "1", 10)
  const status = searchParams.get("status") as TaskStatus | undefined
  const priority = searchParams.get("priority") as TaskPriority | undefined
  const taskType = searchParams.get("task_type") as TaskType | undefined
  const search = searchParams.get("search") || ""

  const { data, isLoading } = useTasks({
    page,
    page_size: PAGE_SIZE,
    status,
    priority,
    task_type: taskType,
    search: search || undefined,
  })

  const completeMutation = useCompleteTask()

  const handleStatusFilter = (newStatus: TaskStatus | null) => {
    const params = new URLSearchParams(searchParams)
    if (newStatus) {
      params.set("status", newStatus)
    } else {
      params.delete("status")
    }
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
    params.set("page", "1")
    setSearchParams(params)
  }

  const handleTypeFilter = (newType: TaskType | null) => {
    const params = new URLSearchParams(searchParams)
    if (newType) {
      params.set("task_type", newType)
    } else {
      params.delete("task_type")
    }
    params.set("page", "1")
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
    params.set("page", "1")
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set("page", String(newPage + 1))
    setSearchParams(params)
  }

  const handleComplete = (id: string) => {
    completeMutation.mutate(id)
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
            {row.original.contact_name && (
              <Link
                to={`/contacts/${row.original.contact}`}
                className="text-sm text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {row.original.contact_name}
              </Link>
            )}
          </div>
        </div>
      ),
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
      cell: ({ row }) => (
        <span className={row.original.is_overdue ? "text-destructive font-medium" : ""}>
          {formatDate(row.original.due_date)}
        </span>
      ),
    },
    {
      accessorKey: "owner_name",
      header: "Assigned To",
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.owner_name}</span>
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
                navigate(`/tasks/${row.original.id}`)
              }}
            >
              View details
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/tasks/${row.original.id}/edit`)
              }}
            >
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {row.original.status !== "completed" && row.original.status !== "cancelled" && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  handleComplete(row.original.id)
                }}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Mark Complete
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
              <h1 className="text-3xl font-semibold tracking-tight">Tasks</h1>
              <p className="text-muted-foreground mt-1">
                Manage your action items and reminders
              </p>
            </div>
            <Button onClick={() => navigate("/tasks/new")}>
              <Plus className="h-4 w-4 mr-2" />
              Create Task
            </Button>
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
                  {(Object.keys(taskStatusLabels) as TaskStatus[]).map((s) => (
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
            onRowClick={(task) => navigate(`/tasks/${task.id}`)}
          />
        </div>
      </Container>
    </Section>
  )
}
