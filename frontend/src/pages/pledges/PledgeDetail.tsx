import { useParams, useNavigate, Link } from "react-router-dom"
import {
  usePledge,
  usePausePledge,
  useResumePledge,
  useCancelPledge,
  useDeletePledge,
} from "@/hooks/usePledges"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowLeft,
  Edit,
  Trash2,
  Pause,
  Play,
  XCircle,
  AlertTriangle,
  User,
  Calendar,
  DollarSign,
} from "lucide-react"
import type { PledgeStatus } from "@/api/pledges"
import { pledgeFrequencyLabels, pledgeStatusLabels } from "@/api/pledges"

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
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
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

export default function PledgeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: pledge, isLoading, error } = usePledge(id!)
  const pauseMutation = usePausePledge()
  const resumeMutation = useResumePledge()
  const cancelMutation = useCancelPledge()
  const deleteMutation = useDeletePledge()

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this pledge? This action cannot be undone.")) {
      deleteMutation.mutate(id!, {
        onSuccess: () => navigate("/pledges"),
      })
    }
  }

  const handleCancel = () => {
    if (window.confirm("Are you sure you want to cancel this pledge?")) {
      cancelMutation.mutate(id!)
    }
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

  if (error || !pledge) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Pledge not found</h1>
            <p className="text-muted-foreground mt-2">
              The pledge you're looking for doesn't exist or you don't have permission to view it.
            </p>
            <Button className="mt-4" onClick={() => navigate("/pledges")}>
              Back to Pledges
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  const isActive = pledge.status === "active"
  const isPaused = pledge.status === "paused"
  const canModifyStatus = isActive || isPaused

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <Link
                to="/pledges"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Pledges
              </Link>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-semibold tracking-tight">
                  {formatCurrency(pledge.amount)} / {pledgeFrequencyLabels[pledge.frequency]}
                </h1>
                <Badge variant={statusVariants[pledge.status]}>
                  {pledgeStatusLabels[pledge.status]}
                </Badge>
                {pledge.is_late && (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    {pledge.days_late} days late
                  </Badge>
                )}
              </div>
              <p className="text-muted-foreground">
                from{" "}
                <Link to={`/contacts/${pledge.contact}`} className="text-primary hover:underline">
                  {pledge.contact_name}
                </Link>
              </p>
            </div>
            <div className="flex gap-2">
              {isActive && (
                <Button
                  variant="secondary"
                  onClick={() => pauseMutation.mutate(id!)}
                  disabled={pauseMutation.isPending}
                >
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
              )}
              {isPaused && (
                <Button
                  variant="secondary"
                  onClick={() => resumeMutation.mutate(id!)}
                  disabled={resumeMutation.isPending}
                >
                  <Play className="h-4 w-4 mr-2" />
                  Resume
                </Button>
              )}
              <Button variant="secondary" onClick={() => navigate(`/pledges/${id}/edit`)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
              {canModifyStatus && (
                <Button
                  variant="secondary"
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                  className="text-destructive hover:text-destructive"
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              )}
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

          {/* Summary Cards */}
          <div className="grid gap-6 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <p className="text-sm text-muted-foreground">Monthly Equivalent</p>
                <p className="text-2xl font-semibold">
                  {formatCurrency(pledge.monthly_equivalent)}
                </p>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <p className="text-sm text-muted-foreground">Total Expected</p>
                <p className="text-2xl font-semibold">
                  {formatCurrency(pledge.total_expected)}
                </p>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <p className="text-sm text-muted-foreground">Total Received</p>
                <p className="text-2xl font-semibold">
                  {formatCurrency(pledge.total_received)}
                </p>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <p className="text-sm text-muted-foreground">Fulfillment</p>
                <p className="text-2xl font-semibold">
                  {Math.round(pledge.fulfillment_percentage)}%
                </p>
                <div className="h-2 bg-muted rounded-full overflow-hidden mt-2">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${Math.min(100, pledge.fulfillment_percentage)}%` }}
                  />
                </div>
              </CardHeader>
            </Card>
          </div>

          {/* Details */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Pledge Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Donor</p>
                    <Link to={`/contacts/${pledge.contact}`} className="font-medium text-primary hover:underline">
                      {pledge.contact_name}
                    </Link>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Amount & Frequency</p>
                    <p className="font-medium">
                      {formatCurrency(pledge.amount)} / {pledgeFrequencyLabels[pledge.frequency]}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Start Date</p>
                    <p className="font-medium">{formatDate(pledge.start_date)}</p>
                  </div>
                </div>
                {pledge.end_date && (
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">End Date</p>
                      <p className="font-medium">{formatDate(pledge.end_date)}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Fulfillment Tracking</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Last Fulfilled</p>
                  <p className="font-medium">{formatDate(pledge.last_fulfilled_date)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Next Expected</p>
                  <p className="font-medium">{formatDate(pledge.next_expected_date)}</p>
                </div>
                {pledge.is_late && (
                  <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                    <div className="flex items-center gap-2 text-destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="font-medium">Payment is {pledge.days_late} days late</span>
                    </div>
                    {pledge.late_notified_at && (
                      <p className="text-sm text-muted-foreground mt-1">
                        Late notification sent: {formatDateTime(pledge.late_notified_at)}
                      </p>
                    )}
                  </div>
                )}
                {pledge.notes && (
                  <div>
                    <p className="text-sm text-muted-foreground">Notes</p>
                    <p className="whitespace-pre-wrap">{pledge.notes}</p>
                  </div>
                )}
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Created: {formatDateTime(pledge.created_at)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Updated: {formatDateTime(pledge.updated_at)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Record Donation Button */}
          {isActive && (
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Record a donation for this pledge</p>
                  <p className="text-sm text-muted-foreground">
                    This will update the fulfillment tracking
                  </p>
                </div>
                <Button onClick={() => navigate(`/donations/new?contact=${pledge.contact}`)}>
                  <DollarSign className="h-4 w-4 mr-2" />
                  Record Donation
                </Button>
              </div>
            </Card>
          )}
        </div>
      </Container>
    </Section>
  )
}
