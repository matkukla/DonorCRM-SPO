import { useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, MessageSquare, Trash2 } from "lucide-react"

import {
  useDeleteFeedback,
  useFeedbackEntry,
  useUpdateFeedback,
} from "@/hooks/useFeedback"
import type { FeedbackStatus } from "@/api/feedback"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const STATUS_VARIANTS: Record<
  FeedbackStatus,
  "default" | "secondary" | "success" | "warning" | "info" | "destructive"
> = {
  new: "warning",
  triaged: "info",
  resolved: "success",
  duplicate: "secondary",
}

export default function AdminFeedbackDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: entry, isLoading } = useFeedbackEntry(id ?? null)
  const updateMutation = useUpdateFeedback()
  const deleteMutation = useDeleteFeedback()

  if (isLoading) {
    return (
      <Section>
        <Container>
          <p className="text-muted-foreground">Loading...</p>
        </Container>
      </Section>
    )
  }

  if (!entry) {
    return (
      <Section>
        <Container>
          <div className="space-y-4">
            <h1 className="text-2xl font-semibold tracking-tight">
              Feedback not found
            </h1>
            <p className="text-muted-foreground">
              This feedback entry no longer exists or you don't have permission
              to view it.
            </p>
            <Button variant="outline" onClick={() => navigate("/admin/feedback")}>
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Back to Feedback
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  const handleStatusChange = (status: FeedbackStatus) => {
    updateMutation.mutate({ id: entry.id, data: { status } })
  }

  const handleDelete = () => {
    if (!window.confirm("Delete this feedback entry? This cannot be undone.")) {
      return
    }
    deleteMutation.mutate(entry.id, {
      onSuccess: () => navigate("/admin/feedback"),
    })
  }

  const submittedOn = new Date(entry.created_at).toLocaleString()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/admin/feedback")}
              className="mb-3 -ml-2"
            >
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Back to Feedback
            </Button>
            <div className="flex items-center gap-3">
              <MessageSquare className="h-7 w-7 text-muted-foreground" />
              <h1 className="text-2xl font-semibold tracking-tight">
                {entry.title}
              </h1>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Badge variant={STATUS_VARIANTS[entry.status]}>
                {entry.status_display}
              </Badge>
              <Badge variant="secondary">{entry.type_display}</Badge>
              <span>•</span>
              <span>Submitted {submittedOn}</span>
            </div>
          </div>

          <Card>
            <CardContent className="pt-6 space-y-6">
              <div>
                <h2 className="text-sm font-medium text-muted-foreground mb-2">
                  Description
                </h2>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">
                  {entry.description}
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-1">
                    Submitter
                  </h3>
                  <p className="text-sm">{entry.submitter_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {entry.submitter_email}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-1">
                    Page URL
                  </h3>
                  <p className="text-sm break-all">
                    {entry.page_url || (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">
                  User Agent
                </h3>
                <p className="text-xs text-muted-foreground break-all">
                  {entry.user_agent || "—"}
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="feedback-status">Update status</Label>
              <Select
                value={entry.status}
                onValueChange={(value) =>
                  handleStatusChange(value as FeedbackStatus)
                }
                disabled={updateMutation.isPending}
              >
                <SelectTrigger id="feedback-status" className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="new">New</SelectItem>
                  <SelectItem value="triaged">Triaged</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="duplicate">Duplicate</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </div>
      </Container>
    </Section>
  )
}
