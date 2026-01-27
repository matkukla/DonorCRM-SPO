import * as React from "react"
import { formatDistanceToNow, format } from "date-fns"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useStageEventsInfinite } from "@/hooks/useJournals"
import { LogEventDialog } from "./LogEventDialog"
import type { PipelineStage, StageEvent } from "@/types/journals"
import { STAGE_LABELS } from "@/types/journals"

export interface EventTimelineDrawerProps {
  /** Journal contact ID to fetch events for */
  journalContactId: string | null
  /** Pipeline stage to filter events */
  stage: PipelineStage | null
  /** Contact name for display */
  contactName: string
  /** Whether the drawer is open */
  isOpen: boolean
  /** Callback to close the drawer */
  onClose: () => void
}

/**
 * Event timeline drawer showing chronological events for a contact's stage.
 *
 * Uses useInfiniteQuery for "Load More" pagination.
 * Per RESEARCH.md: Load 5 events by default with load more option.
 */
export function EventTimelineDrawer({
  journalContactId,
  stage,
  contactName,
  isOpen,
  onClose,
}: EventTimelineDrawerProps) {
  const [logEventOpen, setLogEventOpen] = React.useState(false)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
  } = useStageEventsInfinite(journalContactId ?? "", stage ?? undefined, {
    enabled: isOpen && !!journalContactId,
    pageSize: 5,
  })

  // Flatten pages into single array
  const events = React.useMemo(() => {
    if (!data?.pages) return []
    return data.pages.flatMap((page) => page.results)
  }, [data])

  // Total count from first page
  const totalCount = data?.pages[0]?.count ?? 0

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:w-[400px] overflow-y-auto">
        <SheetHeader className="pb-4 border-b">
          <div className="flex items-start justify-between">
            <div>
              <SheetTitle>
                {stage ? STAGE_LABELS[stage] : "Events"} - {contactName}
              </SheetTitle>
              <SheetDescription>
                {totalCount > 0
                  ? `${totalCount} event${totalCount !== 1 ? "s" : ""} recorded`
                  : "No events recorded yet"}
              </SheetDescription>
            </div>
            <Button
              size="sm"
              onClick={() => setLogEventOpen(true)}
              disabled={!journalContactId}
            >
              Log Event
            </Button>
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-1">
          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              Loading events...
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="flex flex-col items-center justify-center py-8 text-destructive">
              <p>Failed to load events</p>
              <p className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isError && events.length === 0 && (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              No events recorded for this stage yet.
            </div>
          )}

          {/* Event timeline */}
          {events.map((event, index) => (
            <EventCard
              key={event.id}
              event={event}
              isFirst={index === 0}
              isLast={index === events.length - 1 && !hasNextPage}
            />
          ))}

          {/* Load more button */}
          {hasNextPage && (
            <div className="pt-4">
              <Button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                variant="outline"
                className="w-full"
              >
                {isFetchingNextPage ? "Loading..." : "Load More"}
              </Button>
            </div>
          )}
        </div>
      </SheetContent>

      <LogEventDialog
        open={logEventOpen}
        onOpenChange={setLogEventOpen}
        journalContactId={journalContactId || undefined}
        stage={stage || undefined}
      />
    </Sheet>
  )
}

/**
 * Single event card in the timeline.
 */
interface EventCardProps {
  event: StageEvent
  isFirst: boolean
  isLast: boolean
}

function EventCard({ event, isLast }: EventCardProps) {
  // Format event type for display (e.g., "call_logged" -> "Call Logged")
  const eventTypeLabel = event.event_type
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")

  const relativeTime = formatDistanceToNow(new Date(event.created_at), {
    addSuffix: true,
  })

  const absoluteTime = format(new Date(event.created_at), "MMM d, yyyy 'at' h:mm a")

  return (
    <div className="relative pl-6 pb-6">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-[9px] top-4 bottom-0 w-[2px] bg-border" />
      )}

      {/* Timeline dot */}
      <div className="absolute left-0 top-1 w-[18px] h-[18px] rounded-full border-2 border-border bg-background flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-primary" />
      </div>

      {/* Event content */}
      <div className="pt-0">
        <div className="flex items-start justify-between gap-2">
          <Badge variant="secondary" className="text-xs">
            {eventTypeLabel}
          </Badge>
          <span
            className="text-xs text-muted-foreground whitespace-nowrap"
            title={absoluteTime}
          >
            {relativeTime}
          </span>
        </div>

        {event.notes && (
          <p className="mt-2 text-sm text-foreground whitespace-pre-wrap">
            {event.notes}
          </p>
        )}

        {/* Metadata display (if present) */}
        {Object.keys(event.metadata).length > 0 && (
          <div className="mt-2 text-xs text-muted-foreground">
            {Object.entries(event.metadata).map(([key, value]) => (
              <span key={key} className="mr-2">
                {key}: {String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
