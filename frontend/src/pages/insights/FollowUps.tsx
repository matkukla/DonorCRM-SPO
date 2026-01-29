import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useFollowUps } from "@/hooks/useInsights"
import { ListTodo } from "lucide-react"

const priorityLabels: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  urgent: "Urgent",
}

const priorityVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  low: "secondary",
  medium: "outline",
  high: "default",
  urgent: "destructive",
}

const taskTypeLabels: Record<string, string> = {
  call: "Phone Call",
  email: "Email",
  thank_you: "Thank You",
  meeting: "Meeting",
  follow_up: "Follow Up",
  other: "Other",
}

export default function FollowUps() {
  const { data, isLoading, error } = useFollowUps()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Follow-ups</h1>
            <p className="text-muted-foreground mt-1">
              Tasks needing attention
            </p>
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load data. Please try again.
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              Loading...
            </div>
          ) : data && (
            <>
              {/* Summary Cards */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      <ListTodo className="h-5 w-5 text-muted-foreground" />
                      <CardDescription>Total Tasks</CardDescription>
                    </div>
                    <CardTitle className="text-3xl">{data.total_count}</CardTitle>
                  </CardHeader>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription className="text-destructive">Overdue</CardDescription>
                    <CardTitle className="text-3xl text-destructive">{data.overdue_count}</CardTitle>
                  </CardHeader>
                </Card>
              </div>

              {/* Tasks Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Incomplete Tasks</CardTitle>
                  <CardDescription>Sorted by due date</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.tasks.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No pending tasks! You're all caught up.
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Task</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Priority</TableHead>
                          <TableHead>Due Date</TableHead>
                          <TableHead>Contact</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.tasks.map((task) => (
                          <TableRow key={task.id} className={task.is_overdue ? "bg-destructive/5" : ""}>
                            <TableCell>
                              <Link
                                to={`/tasks`}
                                className="font-medium hover:underline text-primary"
                              >
                                {task.title}
                              </Link>
                              {task.description && (
                                <p className="text-sm text-muted-foreground truncate max-w-[300px]">
                                  {task.description}
                                </p>
                              )}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {taskTypeLabels[task.task_type] || task.task_type}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={priorityVariants[task.priority] || "outline"}>
                                {priorityLabels[task.priority] || task.priority}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <span className={task.is_overdue ? "text-destructive font-medium" : ""}>
                                {new Date(task.due_date).toLocaleDateString()}
                              </span>
                              {task.is_overdue && (
                                <Badge variant="destructive" className="ml-2 text-xs">
                                  Overdue
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell>
                              {task.contact_id ? (
                                <Link
                                  to={`/contacts/${task.contact_id}`}
                                  className="hover:underline text-primary"
                                >
                                  {task.contact_name}
                                </Link>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </Container>
    </Section>
  )
}
