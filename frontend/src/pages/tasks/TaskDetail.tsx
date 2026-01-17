import { useParams, useNavigate, Link } from "react-router-dom"
import { useTask, useCompleteTask, useDeleteTask } from "@/hooks/useTasks"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowLeft,
  Edit,
  Trash2,
  CheckCircle,
  AlertTriangle,
  User,
  Calendar,
  Clock,
  Phone,
  Mail,
  Heart,
  Users,
  MessageSquare,
  MoreVertical,
} from "lucide-react"
import type { TaskStatus, TaskPriority, TaskType } from "@/api/tasks"
import { taskStatusLabels, taskPriorityLabels, taskTypeLabels } from "@/api/tasks"

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
  call: <Phone className="h-5 w-5" />,
  email: <Mail className="h-5 w-5" />,
  thank_you: <Heart className="h-5 w-5" />,
  meeting: <Users className="h-5 w-5" />,
  follow_up: <MessageSquare className="h-5 w-5" />,
  other: <MoreVertical className="h-5 w-5" />,
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function formatTime(timeStr: string | null): string {
  if (!timeStr) return ""
  const [hours, minutes] = timeStr.split(":")
  const date = new Date()
  date.setHours(parseInt(hours), parseInt(minutes))
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  })
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: task, isLoading, error } = useTask(id!)
  const completeMutation = useCompleteTask()
  const deleteMutation = useDeleteTask()

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this task? This action cannot be undone.")) {
      deleteMutation.mutate(id!, {
        onSuccess: () => navigate("/tasks"),
      })
    }
  }

  const handleComplete = () => {
    completeMutation.mutate(id!)
  }

  if (isLoading) {
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

  if (error || !task) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Task not found</h1>
            <p className="text-muted-foreground mt-2">
              The task you're looking for doesn't exist or you don't have permission to view it.
            </p>
            <Button className="mt-4" onClick={() => navigate("/tasks")}>
              Back to Tasks
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  const canComplete = task.status !== "completed" && task.status !== "cancelled"

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <Link
                to="/tasks"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Tasks
              </Link>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-muted rounded-lg">
                  {typeIcons[task.task_type]}
                </div>
                <h1 className="text-3xl font-semibold tracking-tight">{task.title}</h1>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={statusVariants[task.status]}>
                  {taskStatusLabels[task.status]}
                </Badge>
                <Badge variant={priorityVariants[task.priority]}>
                  {taskPriorityLabels[task.priority]}
                </Badge>
                <Badge variant="secondary">
                  {taskTypeLabels[task.task_type]}
                </Badge>
                {task.is_overdue && (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Overdue
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              {canComplete && (
                <Button
                  onClick={handleComplete}
                  disabled={completeMutation.isPending}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Complete
                </Button>
              )}
              <Button variant="secondary" onClick={() => navigate(`/tasks/${id}/edit`)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
              <Button
                variant="secondary"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="text-destructive hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Content */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Task Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {task.description && (
                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="whitespace-pre-wrap">{task.description}</p>
                  </div>
                )}
                {task.contact && (
                  <div className="flex items-center gap-3">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Related Contact</p>
                      <Link
                        to={`/contacts/${task.contact}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {task.contact_name}
                      </Link>
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Assigned To</p>
                    <p className="font-medium">{task.owner_name}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Schedule</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Due Date</p>
                    <p className={`font-medium ${task.is_overdue ? "text-destructive" : ""}`}>
                      {formatDate(task.due_date)}
                      {task.due_time && ` at ${formatTime(task.due_time)}`}
                    </p>
                  </div>
                </div>
                {task.reminder_date && (
                  <div className="flex items-center gap-3">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Reminder Date</p>
                      <p className="font-medium">{formatDate(task.reminder_date)}</p>
                    </div>
                  </div>
                )}
                {task.completed_at && (
                  <div className="p-3 bg-success/10 border border-success/20 rounded-lg">
                    <div className="flex items-center gap-2 text-success">
                      <CheckCircle className="h-4 w-4" />
                      <span className="font-medium">Completed</span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {formatDateTime(task.completed_at)}
                    </p>
                  </div>
                )}
                {task.auto_generated && (
                  <div className="p-3 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground">
                      This task was automatically generated
                    </p>
                  </div>
                )}
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Created: {formatDateTime(task.created_at)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Updated: {formatDateTime(task.updated_at)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </Container>
    </Section>
  )
}
