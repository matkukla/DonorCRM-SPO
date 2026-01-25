import { apiClient } from "./client"
import type {
  JournalListItem,
  JournalDetail,
  JournalMember,
  StageEvent,
  StageEventsPage,
  PipelineStage,
  DecisionDetail,
  DecisionCreate,
  DecisionUpdate,
  NextStep,
  NextStepCreate,
  NextStepUpdate,
} from "@/types/journals"

/** Paginated response from DRF */
interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Filter params for journal list */
export interface JournalFilters {
  is_archived?: boolean
  search?: string
}

/** Get paginated list of journals */
export async function getJournals(
  filters: JournalFilters = {}
): Promise<PaginatedResponse<JournalListItem>> {
  const params = new URLSearchParams()
  if (filters.is_archived !== undefined) {
    params.append('is_archived', String(filters.is_archived))
  }
  if (filters.search) {
    params.append('search', filters.search)
  }
  const response = await apiClient.get<PaginatedResponse<JournalListItem>>(
    `/journals/?${params.toString()}`
  )
  return response.data
}

/** Get single journal by ID */
export async function getJournal(id: string): Promise<JournalDetail> {
  const response = await apiClient.get<JournalDetail>(`/journals/${id}/`)
  return response.data
}

/** Create a new journal */
export interface JournalCreate {
  name: string
  goal_amount: string
  deadline?: string | null
}

export async function createJournal(data: JournalCreate): Promise<JournalDetail> {
  const response = await apiClient.post<JournalDetail>('/journals/', data)
  return response.data
}

/** Update a journal */
export type JournalUpdate = Partial<JournalCreate>

export async function updateJournal(
  id: string,
  data: JournalUpdate
): Promise<JournalDetail> {
  const response = await apiClient.patch<JournalDetail>(`/journals/${id}/`, data)
  return response.data
}

/** Archive (soft delete) a journal */
export async function archiveJournal(id: string): Promise<void> {
  await apiClient.delete(`/journals/${id}/`)
}

/** Filter params for journal members */
export interface JournalMemberFilters {
  journal: string
  search?: string
  stage?: PipelineStage
}

/** Get journal members with stage event summaries */
export async function getJournalMembers(
  journalId: string,
  filters: Omit<JournalMemberFilters, 'journal'> = {}
): Promise<PaginatedResponse<JournalMember>> {
  const params = new URLSearchParams()
  params.append('journal', journalId)
  if (filters.search) {
    params.append('search', filters.search)
  }
  if (filters.stage) {
    params.append('stage', filters.stage)
  }
  const response = await apiClient.get<PaginatedResponse<JournalMember>>(
    `/journals/journal-members/?${params.toString()}`
  )
  return response.data
}

/** Get stage events for a journal contact - supports pagination */
export interface StageEventsParams {
  journalContactId: string
  stage?: PipelineStage
  page?: number
  pageSize?: number
}

export async function getStageEvents({
  journalContactId,
  stage,
  page = 1,
  pageSize = 5,
}: StageEventsParams): Promise<StageEventsPage> {
  const params = new URLSearchParams()
  params.append('journal_contact', journalContactId)
  if (stage) {
    params.append('stage', stage)
  }
  params.append('page', String(page))
  params.append('page_size', String(pageSize))

  const response = await apiClient.get<StageEventsPage>(
    `/journals/stage-events/?${params.toString()}`
  )
  return response.data
}

/** Create a stage event */
export interface StageEventCreate {
  journal_contact: string
  stage: PipelineStage
  event_type: string
  notes?: string
  metadata?: Record<string, unknown>
}

export async function createStageEvent(data: StageEventCreate): Promise<StageEvent> {
  const response = await apiClient.post<StageEvent>('/journals/stage-events/', data)
  return response.data
}

/** Create a decision for a journal contact */
export async function createDecision(data: DecisionCreate): Promise<DecisionDetail> {
  const response = await apiClient.post<DecisionDetail>('/journals/decisions/', data)
  return response.data
}

/** Update a decision (triggers history tracking on backend) */
export async function updateDecision(
  id: string,
  data: DecisionUpdate
): Promise<DecisionDetail> {
  const response = await apiClient.patch<DecisionDetail>(
    `/journals/decisions/${id}/`,
    data
  )
  return response.data
}

/** Delete a decision */
export async function deleteDecision(id: string): Promise<void> {
  await apiClient.delete(`/journals/decisions/${id}/`)
}

/** Get a single decision */
export async function getDecision(id: string): Promise<DecisionDetail> {
  const response = await apiClient.get<DecisionDetail>(`/journals/decisions/${id}/`)
  return response.data
}

/** Get next steps for a journal contact */
export async function getNextSteps(
  journalContactId: string
): Promise<PaginatedResponse<NextStep>> {
  const response = await apiClient.get<PaginatedResponse<NextStep>>(
    `/journals/next-steps/?journal_contact=${journalContactId}`
  )
  return response.data
}

/** Create a next step */
export async function createNextStep(data: NextStepCreate): Promise<NextStep> {
  const response = await apiClient.post<NextStep>('/journals/next-steps/', data)
  return response.data
}

/** Update a next step */
export async function updateNextStep(
  id: string,
  data: NextStepUpdate
): Promise<NextStep> {
  const response = await apiClient.patch<NextStep>(
    `/journals/next-steps/${id}/`,
    data
  )
  return response.data
}

/** Delete a next step */
export async function deleteNextStep(id: string): Promise<void> {
  await apiClient.delete(`/journals/next-steps/${id}/`)
}
