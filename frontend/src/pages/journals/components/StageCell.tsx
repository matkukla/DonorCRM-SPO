import * as React from "react"
import { Check } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { StageEventSummary, PipelineStage, FreshnessColor } from "@/types/journals"
import { getFreshnessColor, STAGE_LABELS } from "@/types/journals"

export interface StageCellProps {
  /** Contact ID for click handler */
  contactId: string
  /** Stage this cell represents */
  stage: PipelineStage
  /** Summary of events for this stage */
  eventSummary: StageEventSummary
  /** Click handler to open timeline drawer */
  onCellClick: (contactId: string, stage: PipelineStage) => void
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
  ({ contactId, stage, eventSummary, onCellClick }) => {
    const handleClick = React.useCallback(() => {
      onCellClick(contactId, stage)
    }, [contactId, stage, onCellClick])

    // Empty state - no events logged for this stage
    if (!eventSummary.has_events) {
      return (
        <button
          onClick={handleClick}
          className="h-10 w-10 flex items-center justify-center rounded hover:bg-muted/50 transition-colors"
          aria-label={`${STAGE_LABELS[stage]} - No events`}
        >
          <span className="sr-only">No events</span>
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
  // Custom comparison: only re-render if eventSummary changes
  (prevProps, nextProps) => {
    return (
      prevProps.eventSummary === nextProps.eventSummary &&
      prevProps.contactId === nextProps.contactId &&
      prevProps.stage === nextProps.stage &&
      prevProps.onCellClick === nextProps.onCellClick
    )
  }
)

StageCell.displayName = "StageCell"
