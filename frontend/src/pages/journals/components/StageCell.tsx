import * as React from "react"
import { Check, Square } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { StageEventSummary, PipelineStage } from "@/types/journals"
import {
  getFreshnessColor,
  STAGE_LABELS,
  checkStageTransition,
} from "@/types/journals"

/**
 * Get the highest pipeline stage that has events.
 * Used to determine current stage for transition warnings.
 */
export function getHighestStageWithEvents(
  stageEvents: Record<PipelineStage, StageEventSummary>
): PipelineStage | null {
  const stages: PipelineStage[] = ['next_steps', 'thank', 'decision', 'close', 'meet', 'contact']
  for (const stage of stages) {
    if (stageEvents[stage]?.has_events) {
      return stage
    }
  }
  return null
}

export interface StageCellProps {
  /** Contact ID for click handler */
  contactId: string
  /** Stage this cell represents */
  stage: PipelineStage
  /** Summary of events for this stage */
  eventSummary: StageEventSummary
  /** Click handler to open timeline drawer */
  onCellClick: (contactId: string, stage: PipelineStage) => void
  /** Current highest stage for this contact (for transition warnings) */
  currentStage?: PipelineStage | null
}

/**
 * Memoized stage cell component for journal grid.
 *
 * Performance: Wrapped in React.memo with custom comparison to prevent
 * re-render cascade when other cells change. Only re-renders if this
 * cell's eventSummary changes.
 *
 * From RESEARCH.md: "All function props must be wrapped in useCallback
 * with stable dependencies"
 */
export const StageCell = React.memo<StageCellProps>(
  ({ contactId, stage, eventSummary, onCellClick, currentStage }) => {
    const handleClick = React.useCallback(() => {
      // Check if this would be a non-sequential transition
      // Per JRN-05: "System shows subtle warnings for non-sequential movement (no hard blocks)"
      if (currentStage && stage !== currentStage) {
        const transition = checkStageTransition(currentStage, stage)
        if (!transition.isSequential) {
          if (transition.isRevisiting) {
            toast.warning("Revisiting stage", {
              description: `Moving back to ${STAGE_LABELS[stage]}`,
            })
          } else if (transition.skippedStages.length > 0) {
            toast.warning("Skipping stages", {
              description: `Skipping: ${transition.skippedStages.join(", ")}`,
            })
          }
        }
      }
      // Always proceed - no hard block (per JRN-05)
      onCellClick(contactId, stage)
    }, [contactId, stage, currentStage, onCellClick])

    // Empty state - no events logged for this stage
    if (!eventSummary.has_events) {
      return (
        <button
          onClick={handleClick}
          className="h-10 w-10 flex items-center justify-center rounded hover:bg-muted/50 transition-colors"
          aria-label={`${STAGE_LABELS[stage]} - No events`}
        >
          <Square className="h-5 w-5 text-muted-foreground" />
        </button>
      )
    }

    // Has events - show color-coded checkmark with tooltip
    const freshnessColor = getFreshnessColor(eventSummary.last_event_date)
    const relativeTime = eventSummary.last_event_date
      ? formatDistanceToNow(new Date(eventSummary.last_event_date), { addSuffix: true })
      : null

    // Format event type for display (e.g., "call_logged" -> "Call Logged")
    const eventTypeLabel = eventSummary.last_event_type
      ? eventSummary.last_event_type
          .split('_')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ')
      : 'Event'

    return (
      <TooltipProvider>
        <Tooltip delayDuration={300}>
          <TooltipTrigger asChild>
            <button
              onClick={handleClick}
              className="h-10 w-10 flex items-center justify-center rounded hover:bg-muted/50 transition-colors"
              aria-label={`${STAGE_LABELS[stage]} - ${eventSummary.event_count} events, last ${relativeTime}`}
            >
              <Badge variant={freshnessColor} className="p-1">
                <Check className="h-4 w-4" />
              </Badge>
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <p className="text-sm font-medium">{eventTypeLabel}</p>
            {relativeTime && (
              <p className="text-xs text-muted-foreground">{relativeTime}</p>
            )}
            {eventSummary.last_event_notes && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {eventSummary.last_event_notes}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {eventSummary.event_count} event{eventSummary.event_count !== 1 ? 's' : ''} total
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  },
  // Custom comparison: only re-render if eventSummary or currentStage changes
  (prevProps, nextProps) => {
    return (
      prevProps.eventSummary === nextProps.eventSummary &&
      prevProps.contactId === nextProps.contactId &&
      prevProps.stage === nextProps.stage &&
      prevProps.onCellClick === nextProps.onCellClick &&
      prevProps.currentStage === nextProps.currentStage
    )
  }
)

StageCell.displayName = "StageCell"
