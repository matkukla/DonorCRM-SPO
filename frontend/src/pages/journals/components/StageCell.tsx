import * as React from "react"
import { Check, Square } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { StageEventSummary, PipelineStage, StageEventType } from "@/types/journals"
import { getFreshnessColor, STAGE_LABELS } from "@/types/journals"
import { useCreateStageEvent, useDeleteStageEventsByStage } from "@/hooks/useJournals"
import { useViewAs } from "@/providers/ViewAsProvider"

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

/**
 * Default event type for each stage when auto-creating via checkbox click.
 * These are sensible defaults that create meaningful event records.
 */
function getDefaultEventType(stage: PipelineStage): StageEventType {
  const defaults: Record<PipelineStage, StageEventType> = {
    contact: 'call_logged',
    meet: 'meeting_completed',
    close: 'ask_made',
    decision: 'decision_received',
    thank: 'thank_you_sent',
    next_steps: 'next_step_created',
  }
  return defaults[stage]
}

export interface StageCellProps {
  /** JournalContact ID (through-table), needed for creating stage events */
  journalContactId: string
  /** Stage this cell represents */
  stage: PipelineStage
  /** Summary of events for this stage */
  eventSummary: StageEventSummary
}

/**
 * Memoized stage cell component for journal grid.
 *
 * JRNL-08 behavior:
 * - Unchecked stage (no events): Click immediately creates a stage event
 *   with a default event type. No dialog, no confirmation.
 * - Checked stage (has events): Click deletes all events for this stage (toggle off).
 * - Independent toggles: checking any stage does NOT auto-check others.
 *
 * Performance: Wrapped in React.memo with custom comparison to prevent
 * re-render cascade when other cells change.
 */
export const StageCell = React.memo<StageCellProps>(
  ({ journalContactId, stage, eventSummary }) => {
    const { mutate: createEvent, isPending: isCreating } = useCreateStageEvent()
    const { mutate: deleteEvents, isPending: isDeleting } = useDeleteStageEventsByStage()
    const { isViewingAs } = useViewAs()
    const isPending = isCreating || isDeleting

    const handleClick = React.useCallback(() => {
      if (isViewingAs) return
      if (!eventSummary.has_events) {
        // JRNL-08: Instant toggle -- auto-create stage event, no dialog
        createEvent({
          journal_contact: journalContactId,
          stage,
          event_type: getDefaultEventType(stage),
        })
      } else {
        // Has events -- uncheck by deleting all events for this stage
        deleteEvents({ journalContactId, stage })
      }
    }, [isViewingAs, journalContactId, stage, eventSummary.has_events, createEvent, deleteEvents])

    // Empty state - no events logged for this stage
    if (!eventSummary.has_events) {
      return (
        <button
          onClick={handleClick}
          disabled={isPending}
          className="h-10 w-10 flex items-center justify-center rounded hover:bg-muted/50 transition-colors disabled:opacity-50"
          aria-label={`${STAGE_LABELS[stage]} - Click to mark complete`}
        >
          {isPending ? (
            <div className="h-5 w-5 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin" />
          ) : (
            <Square className="h-5 w-5 text-muted-foreground" />
          )}
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
              disabled={isPending}
              className="h-10 w-10 flex items-center justify-center rounded hover:bg-muted/50 transition-colors disabled:opacity-50"
              aria-label={`${STAGE_LABELS[stage]} - Click to uncheck`}
            >
              {isPending ? (
                <div className="h-5 w-5 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                <Badge variant={freshnessColor} className="p-1">
                  <Check className="h-4 w-4" />
                </Badge>
              )}
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
  // Custom comparison: only re-render if relevant props change
  (prevProps, nextProps) => {
    return (
      prevProps.eventSummary === nextProps.eventSummary &&
      prevProps.journalContactId === nextProps.journalContactId &&
      prevProps.stage === nextProps.stage
    )
  }
)

StageCell.displayName = "StageCell"
