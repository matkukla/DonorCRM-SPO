import * as React from "react"
import { format } from "date-fns"
import { CalendarDays, X } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { useCreateStageEvent } from "@/hooks/useJournals"
import { useContactJournals } from "@/hooks/useContacts"
import type { PipelineStage, StageEventType } from "@/types/journals"
import { PIPELINE_STAGES, STAGE_LABELS } from "@/types/journals"

/** Human-readable labels for event types */
const EVENT_TYPE_LABELS: Record<StageEventType, string> = {
  call_logged: "Call Logged",
  email_sent: "Email Sent",
  text_sent: "Text Sent",
  letter_sent: "Letter Sent",
  meeting_scheduled: "Meeting Scheduled",
  meeting_completed: "Meeting Completed",
  ask_made: "Ask Made",
  follow_up_scheduled: "Follow-up Scheduled",
  follow_up_completed: "Follow-up Completed",
  decision_received: "Decision Received",
  thank_you_sent: "Thank You Sent",
  next_step_created: "Next Step Created",
  note_added: "Note Added",
  other: "Other",
}

const EVENT_TYPES = Object.keys(EVENT_TYPE_LABELS) as StageEventType[]

export interface LogEventDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contactId?: string
  journalContactId?: string
  stage?: PipelineStage
}

export const LogEventDialog = React.memo(function LogEventDialog({
  open,
  onOpenChange,
  contactId,
  journalContactId: preselectedJournalContactId,
  stage: preselectedStage,
}: LogEventDialogProps) {
  // Form state
  const [selectedJournalContactId, setSelectedJournalContactId] = React.useState("")
  const [stage, setStage] = React.useState<PipelineStage>("contact")
  const [eventType, setEventType] = React.useState<StageEventType>("note_added")
  const [notes, setNotes] = React.useState("")
  const [scheduledDate, setScheduledDate] = React.useState<Date | undefined>(undefined)
  const [scheduledTime, setScheduledTime] = React.useState("")
  const [calendarOpen, setCalendarOpen] = React.useState(false)

  // Fetch contact's journals when contactId is provided
  const { data: journals } = useContactJournals(contactId || "")

  // Reset form when dialog opens, and auto-select journal if only one membership
  React.useEffect(() => {
    if (open) {
      setStage(preselectedStage || "contact")
      setEventType(preselectedStage === 'scheduled' ? 'meeting_scheduled' : "note_added")
      setNotes("")
      setScheduledDate(undefined)
      setScheduledTime("")
      setCalendarOpen(false)

      if (preselectedJournalContactId) {
        setSelectedJournalContactId(preselectedJournalContactId)
      } else if (journals?.length === 1) {
        setSelectedJournalContactId(journals[0].id)
      } else {
        setSelectedJournalContactId("")
      }
    }
  }, [open, preselectedJournalContactId, preselectedStage, journals])

  // Auto-set event type when stage changes to 'scheduled'
  React.useEffect(() => {
    if (stage === 'scheduled') {
      setEventType('meeting_scheduled')
    }
  }, [stage])

  const createEventMutation = useCreateStageEvent()
  const isPending = createEventMutation.isPending

  const effectiveJournalContactId = preselectedJournalContactId || selectedJournalContactId

  const isScheduledStage = stage === 'scheduled'
  const canSubmit = !!effectiveJournalContactId && (!isScheduledStage || !!scheduledDate)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!canSubmit) return

    try {
      const payload: Record<string, unknown> = {
        ...(effectiveJournalContactId
          ? { journal_contact: effectiveJournalContactId }
          : { contact_id: contactId }),
        stage,
        event_type: isScheduledStage ? 'meeting_scheduled' : eventType,
        notes: notes || undefined,
      }

      // Per D-13: Include metadata for scheduled stage
      if (isScheduledStage && scheduledDate) {
        payload.metadata = {
          scheduled_date: format(scheduledDate, 'yyyy-MM-dd'),
          ...(scheduledTime ? { scheduled_time: scheduledTime } : {}),
        }
      }

      await createEventMutation.mutateAsync(payload as unknown as Parameters<typeof createEventMutation.mutateAsync>[0])
      onOpenChange(false)
    } catch {
      // Error toast handled by hook
    }
  }

  const needsJournalPicker = !preselectedJournalContactId && journals && journals.length > 1

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Log Event</DialogTitle>
          <DialogDescription>Record an interaction or activity</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Journal picker (only when multiple journals and no pre-selection) */}
          {needsJournalPicker && (
            <div className="space-y-2">
              <Label htmlFor="journal">Journal</Label>
              <Select
                value={selectedJournalContactId}
                onValueChange={setSelectedJournalContactId}
              >
                <SelectTrigger id="journal">
                  <SelectValue placeholder="Select a journal" />
                </SelectTrigger>
                <SelectContent>
                  {journals.map((j) => (
                    <SelectItem key={j.id} value={j.id}>
                      {j.journal_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Stage */}
          <div className="space-y-2">
            <Label htmlFor="stage">Stage</Label>
            <Select
              value={stage}
              onValueChange={(v) => setStage(v as PipelineStage)}
              disabled={preselectedStage === 'scheduled'}
            >
              <SelectTrigger id="stage">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PIPELINE_STAGES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {STAGE_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Event Type */}
          <div className="space-y-2">
            <Label htmlFor="event-type">Event Type</Label>
            <Select
              value={isScheduledStage ? 'meeting_scheduled' : eventType}
              onValueChange={(v) => setEventType(v as StageEventType)}
              disabled={isScheduledStage}
            >
              <SelectTrigger id="event-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EVENT_TYPES.map((et) => (
                  <SelectItem key={et} value={et}>
                    {EVENT_TYPE_LABELS[et]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Date picker (required for scheduled stage) */}
          {isScheduledStage && (
            <div className="space-y-2">
              <Label>Meeting Date <span className="text-destructive">*</span></Label>
              <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !scheduledDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarDays className="mr-2 h-4 w-4" />
                    {scheduledDate ? format(scheduledDate, 'PPP') : 'Pick a date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <div className="flex justify-end border-b p-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      aria-label="Close calendar"
                      onClick={() => setCalendarOpen(false)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <Calendar
                    mode="single"
                    selected={scheduledDate}
                    onSelect={(date) => {
                      setScheduledDate(date)
                      setCalendarOpen(false)
                    }}
                  />
                </PopoverContent>
              </Popover>
            </div>
          )}

          {/* Time input (optional for scheduled stage) */}
          {isScheduledStage && (
            <div className="space-y-2">
              <Label htmlFor="scheduled-time">Meeting Time (optional)</Label>
              <Input
                id="scheduled-time"
                type="time"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
              />
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (optional)</Label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)}
              placeholder="Add details about this interaction..."
              rows={3}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
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
            <Button
              type="submit"
              disabled={isPending || !canSubmit}
            >
              {isPending ? "Saving..." : "Log Event"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
})
