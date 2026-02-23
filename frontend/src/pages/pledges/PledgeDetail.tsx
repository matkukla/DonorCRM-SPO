import { useParams, useNavigate, Link } from "react-router-dom"
import { useRecurringGift, useDeleteRecurringGift } from "@/hooks/useGifts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowLeft,
  Edit,
  Trash2,
  User,
  Calendar,
  DollarSign,
} from "lucide-react"
import type { RecurringGiftStatus } from "@/api/gifts"
import { recurringGiftFrequencyLabels, recurringGiftStatusLabels } from "@/api/gifts"
import { formatLocalDate } from "@/lib/utils"

const statusVariants: Record<RecurringGiftStatus, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  active: "success",
  held: "warning",
  completed: "secondary",
  cancelled: "destructive",
  terminated: "destructive",
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

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return "\u2014"
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

  const { data: rg, isLoading, error } = useRecurringGift(id!)
  const deleteMutation = useDeleteRecurringGift()

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this pledge? This action cannot be undone.")) {
      deleteMutation.mutate(id!, {
        onSuccess: () => navigate("/pledges"),
      })
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

  if (error || !rg) {
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
                  {formatCurrency(rg.amount_dollars)} / {recurringGiftFrequencyLabels[rg.frequency]}
                </h1>
                <Badge variant={statusVariants[rg.status]}>
                  {recurringGiftStatusLabels[rg.status]}
                </Badge>
              </div>
              <p className="text-muted-foreground">
                from{" "}
                <Link to={`/contacts/${rg.donor_contact}`} className="text-primary hover:underline">
                  {rg.donor_contact_name}
                </Link>
                , {recurringGiftFrequencyLabels[rg.frequency].toLowerCase()} since {formatLocalDate(rg.start_date)}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => navigate(`/pledges/${id}/edit`)}>
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
                    <Link to={`/contacts/${rg.donor_contact}`} className="font-medium text-primary hover:underline">
                      {rg.donor_contact_name}
                    </Link>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Amount & Frequency</p>
                    <p className="font-medium">
                      {formatCurrency(rg.amount_dollars)} / {recurringGiftFrequencyLabels[rg.frequency]}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Start Date</p>
                    <p className="font-medium">{formatLocalDate(rg.start_date, "long")}</p>
                  </div>
                </div>
                {rg.end_date && (
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">End Date</p>
                      <p className="font-medium">{formatLocalDate(rg.end_date, "long")}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Additional Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {rg.fund_name && (
                  <div>
                    <p className="text-sm text-muted-foreground">Fund</p>
                    <p className="font-medium">{rg.fund_name}</p>
                  </div>
                )}
                {rg.description && (
                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="whitespace-pre-wrap">{rg.description}</p>
                  </div>
                )}
                {rg.external_gift_id && (
                  <div>
                    <p className="text-sm text-muted-foreground">External Gift ID</p>
                    <p className="font-medium font-mono text-sm">{rg.external_gift_id}</p>
                  </div>
                )}
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Created: {formatDateTime(rg.created_at)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Updated: {formatDateTime(rg.updated_at)}
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
