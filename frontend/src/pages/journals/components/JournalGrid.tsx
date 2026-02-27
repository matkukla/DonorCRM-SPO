import * as React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { StageCell, getHighestStageWithEvents } from "./StageCell"
import { ContactNameCell } from "./ContactNameCell"
import { DecisionCell } from "./DecisionCell"
import { NextStepsCell } from "./NextStepsCell"
import type { JournalMember, PipelineStage, StageEventSummary } from "@/types/journals"
import { STAGE_LABELS } from "@/types/journals"

/**
 * Stage columns rendered as checkboxes in the grid, split around the Decision card.
 * Excludes 'decision' -- that stage is replaced by the DecisionCell card
 * positioned between Close and Thank per JRNL-07.
 */
const STAGES_BEFORE_DECISION: PipelineStage[] = ['contact', 'meet', 'close']
const STAGES_AFTER_DECISION: PipelineStage[] = ['thank']

export interface JournalGridProps {
  /** Journal members to display as rows */
  members: JournalMember[]
  /** Journal ID for decision hooks */
  journalId: string
  /** Callback when a stage cell is clicked (opens timeline drawer) */
  onStageCellClick: (contactId: string, stage: PipelineStage) => void
  /** Loading state */
  isLoading?: boolean
}

/**
 * Journal grid component displaying contacts as rows, stages as columns.
 *
 * Implements sticky headers and first column per RESEARCH.md:
 * - Header row: sticky top-0 z-10
 * - Contact name column: sticky left-0 z-20
 * - Header/column intersection: sticky top-0 left-0 z-30
 *
 * Z-index hierarchy prevents overlap issues during scroll.
 */
export function JournalGrid({
  members,
  journalId,
  onStageCellClick,
  isLoading = false,
}: JournalGridProps) {
  // Memoize click handler to prevent StageCell re-renders
  const handleCellClick = React.useCallback(
    (contactId: string, stage: PipelineStage) => {
      onStageCellClick(contactId, stage)
    },
    [onStageCellClick]
  )

  // Empty state
  if (!isLoading && members.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        No contacts in this journal. Add contacts to get started.
      </div>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        Loading contacts...
      </div>
    )
  }

  return (
    <div className="relative w-full overflow-x-auto border rounded-lg">
      <Table className="min-w-[1100px]" aria-label="Journal grid">
        <TableHeader>
          <TableRow className="bg-background">
            {/* Intersection cell: sticky both directions, highest z-index */}
            <TableHead className="sticky top-0 left-0 z-30 bg-background min-w-[200px] w-[200px] border-r">
              Contact
            </TableHead>
            {/* Stage columns before Decision: contact, meet, close */}
            {STAGES_BEFORE_DECISION.map((stage) => (
              <TableHead
                key={stage}
                className="sticky top-0 z-10 bg-background text-center min-w-[100px] w-[100px]"
              >
                {STAGE_LABELS[stage]}
              </TableHead>
            ))}
            {/* Decision column (repositioned between Close and Thank) */}
            <TableHead className="sticky top-0 z-10 bg-background text-center min-w-[140px] w-[140px]">
              Decision
            </TableHead>
            {/* Stage columns after Decision: thank, next_steps */}
            {STAGES_AFTER_DECISION.map((stage) => (
              <TableHead
                key={stage}
                className="sticky top-0 z-10 bg-background text-center min-w-[100px] w-[100px]"
              >
                {STAGE_LABELS[stage]}
              </TableHead>
            ))}
            {/* Next Steps checklist column */}
            <TableHead className="sticky top-0 z-10 bg-background text-center min-w-[100px] w-[100px]">
              Next Steps
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((member) => {
            const currentStage = getHighestStageWithEvents(member.stage_events)
            return (
              <TableRow key={member.id}>
                {/* Contact name cell: sticky left only */}
                <TableCell className="sticky left-0 z-20 bg-background border-r min-w-[200px] w-[200px]">
                  <ContactNameCell
                    name={member.contact_name}
                    email={member.contact_email}
                    status={member.contact_status}
                  />
                </TableCell>
                {/* Stage cells before Decision: contact, meet, close */}
                {STAGES_BEFORE_DECISION.map((stage) => {
                  const eventSummary = getStageEventSummary(member, stage)
                  return (
                    <TableCell key={stage} className="p-2 min-w-[100px] w-[100px]">
                      <div className="flex items-center justify-center">
                        <StageCell
                          contactId={member.contact}
                          journalContactId={member.id}
                          stage={stage}
                          eventSummary={eventSummary}
                          currentStage={currentStage}
                          onCellClick={handleCellClick}
                        />
                      </div>
                    </TableCell>
                  )
                })}
                {/* Decision cell (repositioned between Close and Thank) */}
                <TableCell className="p-2 min-w-[140px] w-[140px]">
                  <DecisionCell
                    decision={member.decision}
                    journalContactId={member.id}
                    journalId={journalId}
                    contactName={member.contact_name}
                  />
                </TableCell>
                {/* Stage cells after Decision: thank, next_steps */}
                {STAGES_AFTER_DECISION.map((stage) => {
                  const eventSummary = getStageEventSummary(member, stage)
                  return (
                    <TableCell key={stage} className="p-2 min-w-[100px] w-[100px]">
                      <div className="flex items-center justify-center">
                        <StageCell
                          contactId={member.contact}
                          journalContactId={member.id}
                          stage={stage}
                          eventSummary={eventSummary}
                          currentStage={currentStage}
                          onCellClick={handleCellClick}
                        />
                      </div>
                    </TableCell>
                  )
                })}
                {/* Next Steps checklist cell */}
                <TableCell className="p-2 min-w-[100px] w-[100px]">
                  <div className="flex items-center justify-center">
                    <NextStepsCell journalContactId={member.id} />
                  </div>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

/**
 * Helper to extract stage event summary from member data.
 * Returns empty summary if stage has no events.
 */
function getStageEventSummary(
  member: JournalMember,
  stage: PipelineStage
): StageEventSummary {
  const summary = member.stage_events?.[stage]
  if (summary) {
    return summary
  }
  // Default empty summary
  return {
    has_events: false,
    event_count: 0,
    last_event_date: null,
    last_event_type: null,
    last_event_notes: null,
  }
}
