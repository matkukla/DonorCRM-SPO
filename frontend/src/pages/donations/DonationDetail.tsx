import { useParams, useNavigate, Link } from "react-router-dom"
import { useDonation, useMarkDonationThanked, useDeleteDonation } from "@/hooks/useDonations"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeft, Edit, Trash2, Check, User, Calendar, CreditCard, FileText } from "lucide-react"
import { donationTypeLabels, paymentMethodLabels } from "@/api/donations"

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

export default function DonationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: donation, isLoading, error } = useDonation(id!)
  const markThankedMutation = useMarkDonationThanked()
  const deleteMutation = useDeleteDonation()

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this donation? This action cannot be undone.")) {
      deleteMutation.mutate(id!, {
        onSuccess: () => navigate("/donations"),
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

  if (error || !donation) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Donation not found</h1>
            <p className="text-muted-foreground mt-2">
              The donation you're looking for doesn't exist or you don't have permission to view it.
            </p>
            <Button className="mt-4" onClick={() => navigate("/donations")}>
              Back to Donations
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
                to="/donations"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Donations
              </Link>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-semibold tracking-tight">
                  {formatCurrency(donation.amount)}
                </h1>
                {donation.thanked ? (
                  <Badge variant="success" className="gap-1">
                    <Check className="h-3 w-3" />
                    Thanked
                  </Badge>
                ) : (
                  <Badge variant="warning">Pending Thank You</Badge>
                )}
              </div>
              <p className="text-muted-foreground">
                from{" "}
                <Link to={`/contacts/${donation.contact}`} className="text-primary hover:underline">
                  {donation.contact_name}
                </Link>
                {" "}on {formatDate(donation.date)}
              </p>
            </div>
            <div className="flex gap-2">
              {!donation.thanked && (
                <Button
                  variant="secondary"
                  onClick={() => markThankedMutation.mutate(id!)}
                  disabled={markThankedMutation.isPending}
                >
                  <Check className="h-4 w-4 mr-2" />
                  Mark Thanked
                </Button>
              )}
              <Button variant="secondary" onClick={() => navigate(`/donations/${id}/edit`)}>
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
                <CardTitle>Donation Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Donor</p>
                    <Link to={`/contacts/${donation.contact}`} className="font-medium text-primary hover:underline">
                      {donation.contact_name}
                    </Link>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Date</p>
                    <p className="font-medium">{formatDate(donation.date)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Type</p>
                    <p className="font-medium">{donationTypeLabels[donation.donation_type]}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <CreditCard className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Payment Method</p>
                    <p className="font-medium">{paymentMethodLabels[donation.payment_method]}</p>
                  </div>
                </div>
                {donation.external_id && (
                  <div>
                    <p className="text-sm text-muted-foreground">External ID</p>
                    <p className="font-medium font-mono text-sm">{donation.external_id}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Status & Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {donation.pledge_info && (
                  <div>
                    <p className="text-sm text-muted-foreground">Linked Pledge</p>
                    <Link
                      to={`/pledges/${donation.pledge_info.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {formatCurrency(donation.pledge_info.amount)} / {donation.pledge_info.frequency}
                    </Link>
                  </div>
                )}
                <div>
                  <p className="text-sm text-muted-foreground">Thank You Status</p>
                  {donation.thanked ? (
                    <p className="font-medium">
                      Thanked on {formatDateTime(donation.thanked_at)}
                    </p>
                  ) : (
                    <p className="font-medium text-amber-600">Pending</p>
                  )}
                </div>
                {donation.notes && (
                  <div>
                    <p className="text-sm text-muted-foreground">Notes</p>
                    <p className="whitespace-pre-wrap">{donation.notes}</p>
                  </div>
                )}
                {donation.imported_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Import Info</p>
                    <p className="text-sm">
                      Imported on {formatDateTime(donation.imported_at)}
                      {donation.import_batch && (
                        <span className="text-muted-foreground"> (Batch: {donation.import_batch})</span>
                      )}
                    </p>
                  </div>
                )}
                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Created: {formatDateTime(donation.created_at)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Updated: {formatDateTime(donation.updated_at)}
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
