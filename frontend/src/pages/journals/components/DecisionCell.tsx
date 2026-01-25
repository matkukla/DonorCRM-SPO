import * as React from "react"
import { Plus } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DecisionDialog } from "./DecisionDialog"
import type { DecisionSummary, DecisionStatus } from "@/types/journals"
import { CADENCE_LABELS, STATUS_LABELS } from "@/types/journals"

export interface DecisionCellProps {
  /** Decision for this cell, or null if no decision yet */
  decision: DecisionSummary | null
  /** Journal contact ID */
  journalContactId: string
  /** Journal ID */
  journalId: string
  /** Contact name for dialog display */
  contactName: string
}

/**
 * Get badge variant based on decision status.
 * Maps status to badge variants matching our color scheme.
 */
function getStatusBadgeVariant(status: DecisionStatus): "success" | "warning" | "secondary" | "destructive" {
  switch (status) {
    case "active":
      return "success"
    case "pending":
      return "warning"
    case "paused":
      return "secondary"
    case "declined":
      return "destructive"
    default:
      return "secondary"
  }
}

/**
 * Decision cell component for the journal grid.
 *
 * Per JRN-13:
 * - Decision column shows card with amount, cadence, and status
 * - User can click to open decision update dialog
 * - Card uses color coding for status (pending/active/paused/declined)
 *
 * Memoized to prevent cascade re-renders per success criteria #7.
 */
export const DecisionCell = React.memo(function DecisionCell({
  decision,
  journalContactId,
  journalId,
  contactName,
}: DecisionCellProps) {
  const [dialogOpen, setDialogOpen] = React.useState(false)

  // Empty state - show add button
  if (!decision) {
    return (
      <>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDialogOpen(true)}
          className="text-muted-foreground hover:text-foreground"
        >
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>

        <DecisionDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          decision={null}
          journalContactId={journalContactId}
          journalId={journalId}
          contactName={contactName}
        />
      </>
    )
  }

  // Has decision - show card
  return (
    <>
      <button
        onClick={() => setDialogOpen(true)}
        className="w-full p-2 rounded-md border bg-card hover:bg-accent transition-colors text-left space-y-1"
        aria-label={`Edit decision: $${parseFloat(decision.amount).toLocaleString()} ${CADENCE_LABELS[decision.cadence]}, ${STATUS_LABELS[decision.status]}`}
      >
        {/* Amount */}
        <div className="font-semibold text-sm">
          ${parseFloat(decision.amount).toLocaleString()}
        </div>

        {/* Cadence */}
        <div className="text-xs text-muted-foreground">
          {CADENCE_LABELS[decision.cadence]}
        </div>

        {/* Status badge */}
        <Badge variant={getStatusBadgeVariant(decision.status)} className="text-xs">
          {STATUS_LABELS[decision.status]}
        </Badge>

        {/* Monthly equivalent (for non-one-time) */}
        {decision.cadence !== "one_time" && parseFloat(decision.monthly_equivalent) > 0 && (
          <div className="text-xs text-muted-foreground">
            ${parseFloat(decision.monthly_equivalent).toLocaleString()}/mo
          </div>
        )}
      </button>

      <DecisionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        decision={decision}
        journalContactId={journalContactId}
        journalId={journalId}
        contactName={contactName}
      />
    </>
  )
})
