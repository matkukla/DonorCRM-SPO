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
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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

  // Fetch contact's journals when contactId is provided
  const { data: journals } = useContactJournals(contactId || "")

  // Auto-select journal if contact has only one membership
  React.useEffect(() => {
    if (journals?.length === 1 && !preselectedJournalContactId) {
      setSelectedJournalContactId(journals[0].id)
    }
  }, [journals, preselectedJournalContactId])

  // Reset form when dialog opens
  React.useEffect(() => {
    if (open) {
      setSelectedJournalContactId(preselectedJournalContactId || "")
      setStage(preselectedStage || "contact")
      setEventType("note_added")
      setNotes("")
    }
  }, [open, preselectedJournalContactId, preselectedStage])

  const createEventMutation = useCreateStageEvent()
  const isPending = createEventMutation.isPending

  const effectiveJournalContactId = preselectedJournalContactId || selectedJournalContactId

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!effectiveJournalContactId) return

    try {
      await createEventMutation.mutateAsync({
        journal_contact: effectiveJournalContactId,
        stage,
        event_type: eventType,
        notes: notes || undefined,
      })
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

          {/* No journals message */}
          {!preselectedJournalContactId && journals && journals.length === 0 && (
            <p className="text-sm text-muted-foreground">
              This contact is not enrolled in any journals.
            </p>
          )}

          {/* Stage */}
          <div className="space-y-2">
            <Label htmlFor="stage">Stage</Label>
            <Select
              value={stage}
              onValueChange={(v) => setStage(v as PipelineStage)}
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
              value={eventType}
              onValueChange={(v) => setEventType(v as StageEventType)}
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
              disabled={isPending || !effectiveJournalContactId}
            >
              {isPending ? "Saving..." : "Log Event"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
})
