import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCreateDecision, useUpdateDecision } from "@/hooks/useJournals"
import type {
  DecisionSummary,
  DecisionCadence,
  DecisionStatus,
} from "@/types/journals"
import { CADENCE_LABELS, STATUS_LABELS } from "@/types/journals"

export interface DecisionDialogProps {
  /** Whether the dialog is open */
  open: boolean
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void
  /** Existing decision to edit, or null for create */
  decision: DecisionSummary | null
  /** Journal contact ID for creating new decisions */
  journalContactId: string
  /** Journal ID for hooks */
  journalId: string
  /** Contact name for display */
  contactName: string
}

/**
 * Dialog for creating or editing a decision.
 *
 * Per JRN-13: "User can click to open decision update dialog"
 *
 * Features:
 * - Edit mode: Pre-fills form with existing decision
 * - Create mode: Empty form for new decision
 * - Uses optimistic updates via hooks
 */
export const DecisionDialog = React.memo(function DecisionDialog({
  open,
  onOpenChange,
  decision,
  journalContactId,
  journalId,
  contactName,
}: DecisionDialogProps) {
  const isEdit = !!decision

  // Form state
  const [amount, setAmount] = React.useState("")
  const [cadence, setCadence] = React.useState<DecisionCadence>("monthly")
  const [status, setStatus] = React.useState<DecisionStatus>("pending")

  // Reset form when dialog opens or decision changes
  React.useEffect(() => {
    if (open) {
      if (decision) {
        setAmount(decision.amount)
        setCadence(decision.cadence)
        setStatus(decision.status)
      } else {
        setAmount("")
        setCadence("monthly")
        setStatus("pending")
      }
    }
  }, [open, decision])

  const createMutation = useCreateDecision(journalId)
  const updateMutation = useUpdateDecision(journalId)

  const isPending = createMutation.isPending || updateMutation.isPending

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!amount || parseFloat(amount) <= 0) {
      return
    }

    try {
      if (isEdit && decision) {
        await updateMutation.mutateAsync({
          id: decision.id,
          data: { amount, cadence, status },
        })
      } else {
        await createMutation.mutateAsync({
          journal_contact: journalContactId,
          amount,
          cadence,
          status,
        })
      }
      onOpenChange(false)
    } catch {
      // Error toast handled by hook
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Edit Decision" : "Add Decision"}
          </DialogTitle>
          <DialogDescription>{contactName}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                id="amount"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="pl-7"
                placeholder="0.00"
                required
              />
            </div>
          </div>

          {/* Cadence */}
          <div className="space-y-2">
            <Label htmlFor="cadence">Cadence</Label>
            <Select value={cadence} onValueChange={(v) => setCadence(v as DecisionCadence)}>
              <SelectTrigger id="cadence">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(CADENCE_LABELS) as DecisionCadence[]).map((c) => (
                  <SelectItem key={c} value={c}>
                    {CADENCE_LABELS[c]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={(v) => setStatus(v as DecisionStatus)}>
              <SelectTrigger id="status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(STATUS_LABELS) as DecisionStatus[]).map((s) => (
                  <SelectItem key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Saving..." : isEdit ? "Save Changes" : "Create Decision"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
})
