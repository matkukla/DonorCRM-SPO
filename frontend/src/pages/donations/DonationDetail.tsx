import { useParams, useNavigate, Link } from "react-router-dom"
import { useGift, useDeleteGift } from "@/hooks/useGifts"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Edit, Trash2, User, Calendar, FileText, Hash, DollarSign, CreditCard } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"

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

interface DonationDetailPanelProps {
  open: boolean
  giftId: string | null
  onClose: () => void
}

export function DonationDetailPanel({ open, giftId, onClose }: DonationDetailPanelProps) {
  const navigate = useNavigate()
  const { data: gift, isLoading } = useGift(giftId)
  const deleteMutation = useDeleteGift()

  const handleDelete = () => {
    if (!giftId) return
    if (window.confirm("Are you sure you want to delete this donation? This action cannot be undone.")) {
      deleteMutation.mutate(giftId, {
        onSuccess: () => onClose(),
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        {isLoading ? (
          <div className="space-y-6">
            <div className="h-16 bg-muted rounded animate-pulse" />
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-muted rounded animate-pulse" />
              ))}
            </div>
            <div className="h-32 bg-muted rounded animate-pulse" />
          </div>
        ) : gift ? (
          <div className="space-y-6">
            <DialogHeader>
              <DialogTitle>{formatCurrency(gift.amount_dollars)}</DialogTitle>
              <DialogDescription>
                from {gift.donor_contact_name} on {formatLocalDate(gift.gift_date)}
              </DialogDescription>
            </DialogHeader>

            {/* Details */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Donation Details</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm text-muted-foreground">Donor</p>
                    <Link
                      to={`/contacts/${gift.donor_contact}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {gift.donor_contact_name}
                    </Link>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm text-muted-foreground">Date</p>
                    <p className="font-medium">{formatLocalDate(gift.gift_date, "long")}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <CreditCard className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm text-muted-foreground">Payment Type</p>
                    <p className="font-medium">{gift.payment_type_display || "---"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <DollarSign className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm text-muted-foreground">Fund</p>
                    <p className="font-medium">{gift.fund_name || "No fund"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="font-medium">{gift.description || "No description"}</p>
                  </div>
                </div>
                {gift.external_gift_id && (
                  <div className="flex items-center gap-3">
                    <Hash className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div>
                      <p className="text-sm text-muted-foreground">External ID</p>
                      <p className="font-medium font-mono text-sm">{gift.external_gift_id}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Solicitor Credits -- only shown when credits exist */}
            {gift.credits && gift.credits.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold">Solicitor Credits</h3>
                <div className="rounded-lg border">
                  <Table aria-label="Solicitor credits">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Solicitor Name</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">Percentage</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {gift.credits.map((credit) => (
                        <TableRow key={credit.id}>
                          <TableCell className="font-medium">{credit.solicitor_name}</TableCell>
                          <TableCell className="text-right">{formatCurrency(credit.amount_dollars)}</TableCell>
                          <TableCell className="text-right">
                            {(credit.amount_cents / gift.amount_cents * 100).toFixed(1)}%
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Actions</h3>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => navigate(`/donations/${giftId}/edit`)}
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Timestamps */}
            <div className="pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Created: {formatDateTime(gift.created_at)}
              </p>
              <p className="text-sm text-muted-foreground">
                Updated: {formatDateTime(gift.updated_at)}
              </p>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

// Backward-compatible default export for /donations/:id route
export default function DonationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  return (
    <DonationDetailPanel
      open={true}
      giftId={id || null}
      onClose={() => navigate("/donations")}
    />
  )
}
