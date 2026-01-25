/**
 * TypeScript types for Journal Grid UI.
 * Maps to Django models: Journal, JournalContact, JournalStageEvent, Decision
 */

/** Pipeline stages matching PipelineStage Django TextChoices */
export type PipelineStage =
  | 'contact'
  | 'meet'
  | 'close'
  | 'decision'
  | 'thank'
  | 'next_steps'

/** Stage event types matching StageEventType Django TextChoices */
export type StageEventType =
  | 'call_logged'
  | 'email_sent'
  | 'text_sent'
  | 'letter_sent'
  | 'meeting_scheduled'
  | 'meeting_completed'
  | 'ask_made'
  | 'follow_up_scheduled'
  | 'follow_up_completed'
  | 'decision_received'
  | 'thank_you_sent'
  | 'next_step_created'
  | 'note_added'
  | 'other'

/** Decision cadence options */
export type DecisionCadence = 'one_time' | 'monthly' | 'quarterly' | 'annual'

/** Decision status options */
export type DecisionStatus = 'pending' | 'active' | 'paused' | 'declined'

/** Freshness color based on days since last event */
export type FreshnessColor = 'success' | 'warning' | 'orange' | 'destructive' | 'secondary'

/** Journal list item from API */
export interface JournalListItem {
  id: string
  name: string
  goal_amount: string
  deadline: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
}

/** Journal detail from API */
export interface JournalDetail extends JournalListItem {
  owner: string
  archived_at: string | null
}

/** Journal contact member with stage events summary */
export interface JournalMember {
  id: string
  journal: string
  contact: string
  contact_name: string
  contact_email: string | null
  contact_status: string
  created_at: string
  /** Stage events grouped by stage for grid display */
  stage_events: Record<PipelineStage, StageEventSummary>
  /** Current decision for this contact (if any) */
  decision: DecisionSummary | null
}

/** Summary of events for a single stage cell */
export interface StageEventSummary {
  has_events: boolean
  event_count: number
  last_event_date: string | null
  last_event_type: StageEventType | null
  last_event_notes: string | null
}

/** Stage event from API */
export interface StageEvent {
  id: string
  journal_contact: string
  stage: PipelineStage
  event_type: StageEventType
  notes: string
  metadata: Record<string, unknown>
  triggered_by: string | null
  created_at: string
}

/** Paginated stage events response */
export interface StageEventsPage {
  count: number
  next: string | null
  previous: string | null
  results: StageEvent[]
}

/** Decision summary for grid display */
export interface DecisionSummary {
  id: string
  amount: string
  cadence: DecisionCadence
  status: DecisionStatus
  monthly_equivalent: string
}

/** Full decision detail from API */
export interface DecisionDetail {
  id: string
  journal_contact: string
  amount: string
  cadence: DecisionCadence
  status: DecisionStatus
  monthly_equivalent: string
  created_at: string
  updated_at: string
}

/** Decision create payload */
export interface DecisionCreate {
  journal_contact: string
  amount: string
  cadence: DecisionCadence
  status: DecisionStatus
}

/** Decision update payload (partial) */
export interface DecisionUpdate {
  amount?: string
  cadence?: DecisionCadence
  status?: DecisionStatus
}

/** Decision status display colors */
export const DECISION_STATUS_COLORS: Record<DecisionStatus, string> = {
  pending: 'warning',
  active: 'success',
  paused: 'secondary',
  declined: 'destructive',
}

/** Decision cadence labels for display */
export const CADENCE_LABELS: Record<DecisionCadence, string> = {
  one_time: 'One-Time',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  annual: 'Annual',
}

/** Decision status labels for display */
export const STATUS_LABELS: Record<DecisionStatus, string> = {
  pending: 'Pending',
  active: 'Active',
  paused: 'Paused',
  declined: 'Declined',
}

/** Props for freshness color calculation */
export function getFreshnessColor(lastEventDate: string | null): FreshnessColor {
  if (!lastEventDate) return 'secondary'

  const now = new Date()
  const eventDate = new Date(lastEventDate)
  const daysSince = Math.floor((now.getTime() - eventDate.getTime()) / (1000 * 60 * 60 * 24))

  if (daysSince < 7) return 'success'      // Green: <1 week
  if (daysSince < 30) return 'warning'     // Yellow/Amber: <1 month
  if (daysSince < 90) return 'orange'      // Orange: <3 months
  return 'destructive'                     // Red: 3+ months
}

/** Human-readable stage labels */
export const STAGE_LABELS: Record<PipelineStage, string> = {
  contact: 'Contact',
  meet: 'Meet',
  close: 'Close',
  decision: 'Decision',
  thank: 'Thank',
  next_steps: 'Next Steps',
}

/** Ordered list of stages for grid columns */
export const PIPELINE_STAGES: PipelineStage[] = [
  'contact',
  'meet',
  'close',
  'decision',
  'thank',
  'next_steps',
]
