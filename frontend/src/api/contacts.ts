import { apiClient } from "./client"

export type ContactStatus = "prospect" | "donor" | "lapsed" | "major_donor" | "deceased"

export interface ContactListItem {
  id: string
  first_name: string
  last_name: string
  full_name: string
  organization_name?: string
  email: string | null
  phone: string | null
  status: ContactStatus
  total_given: string
  gift_count: number
  last_gift_date: string | null
  needs_thank_you: boolean
  owner: string
  owner_name: string
}

export interface ContactDetail extends ContactListItem {
  phone_secondary: string | null
  street_address: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  country: string
  full_address: string | null
  first_gift_date: string | null
  last_gift_amount: string | null
  has_active_pledge: boolean
  monthly_pledge_amount: string | null
  last_thanked_at: string | null
  notes: string | null
  external_id: string | null
  external_constituent_id: string | null
  groups: Array<{ id: string; name: string; description: string | null }>
  created_at: string
  updated_at: string
}

export interface ContactCreate {
  first_name: string
  last_name: string
  organization_name?: string
  email?: string
  phone?: string
  phone_secondary?: string
  street_address?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string
  status?: ContactStatus
  notes?: string
  group_ids?: string[]
}

export interface ContactUpdate extends Partial<ContactCreate> {}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Confidence tier for duplicate matching */
export type DuplicateConfidence = "high" | "medium" | "low"

/** Single duplicate match from pre-creation check */
export interface DuplicateMatch {
  id: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  organization_name: string
  status: ContactStatus
  confidence: DuplicateConfidence
  reasons: string[]
  similarity: number
}

/** A pair of potential duplicate contacts from batch scan */
export interface DuplicatePair {
  contact_a: ContactListItem
  contact_b: ContactListItem
  confidence: DuplicateConfidence
  reasons: string[]
  similarity: number
}

/** Input for merge operation */
export interface MergeRequest {
  survivor_id: string
  loser_id: string
}

/** Input for dismissing a duplicate pair */
export interface DismissRequest {
  contact_a_id: string
  contact_b_id: string
}

export interface ContactFilters {
  search?: string
  status?: ContactStatus
  needs_thank_you?: boolean
  group?: string
  owner?: string
  ordering?: string
  last_gift_after?: string
  last_gift_before?: string
  page?: number
  page_size?: number
}

/**
 * List contacts with optional filters
 */
export async function getContacts(params: Record<string, string> = {}): Promise<PaginatedResponse<ContactListItem>> {
  const response = await apiClient.get<PaginatedResponse<ContactListItem>>("/contacts/", { params })
  return response.data
}

/**
 * Get a single contact by ID
 */
export async function getContact(id: string): Promise<ContactDetail> {
  const response = await apiClient.get<ContactDetail>(`/contacts/${id}/`)
  return response.data
}

/**
 * Create a new contact
 */
export async function createContact(data: ContactCreate): Promise<ContactDetail> {
  const response = await apiClient.post<ContactDetail>("/contacts/", data)
  return response.data
}

/**
 * Update a contact
 */
export async function updateContact(id: string, data: ContactUpdate): Promise<ContactDetail> {
  const response = await apiClient.patch<ContactDetail>(`/contacts/${id}/`, data)
  return response.data
}

/**
 * Delete a contact
 */
export async function deleteContact(id: string): Promise<void> {
  await apiClient.delete(`/contacts/${id}/`)
}

/**
 * Mark a contact as thanked
 */
export async function markContactThanked(id: string): Promise<void> {
  await apiClient.post(`/contacts/${id}/thank/`)
}

/**
 * Search contacts
 */
export async function searchContacts(query: string): Promise<ContactListItem[]> {
  const response = await apiClient.get<ContactListItem[]>("/contacts/search/", {
    params: { q: query },
  })
  return response.data
}

/**
 * Get contact's donations
 */
export async function getContactDonations(id: string) {
  const response = await apiClient.get(`/contacts/${id}/donations/`)
  return response.data
}

/**
 * Get contact's pledges
 */
export async function getContactPledges(id: string) {
  const response = await apiClient.get(`/contacts/${id}/pledges/`)
  return response.data
}

/**
 * Get contact's tasks
 */
export async function getContactTasks(id: string) {
  const response = await apiClient.get(`/contacts/${id}/tasks/`)
  return response.data
}

/** Journal event for a contact (across all journal memberships) */
export interface ContactJournalEvent {
  id: string
  event_type: string
  stage: string
  notes: string
  metadata: Record<string, unknown>
  created_at: string
  journal_name: string
  journal_id: string
  journal_contact_id: string
}

/** Get paginated journal events for a contact */
export async function getContactJournalEvents(
  contactId: string,
  page = 1,
  pageSize = 10
): Promise<PaginatedResponse<ContactJournalEvent>> {
  const response = await apiClient.get<PaginatedResponse<ContactJournalEvent>>(
    `/contacts/${contactId}/journal-events/?page=${page}&page_size=${pageSize}`
  )
  return response.data
}

/** Journal membership for a contact */
export interface ContactJournalMembership {
  id: string
  journal_id: string
  journal_name: string
  goal_amount: string
  deadline: string | null
  current_stage: string
  decision: {
    id: string
    amount: string
    cadence: string
    status: string
  } | null
  created_at: string
}

/** Get journals a contact belongs to */
export async function getContactJournals(contactId: string): Promise<ContactJournalMembership[]> {
  const response = await apiClient.get<ContactJournalMembership[]>(
    `/contacts/${contactId}/journals/`
  )
  return response.data
}

/** Get email addresses for contacts matching the given filters */
export async function getContactEmails(params: Record<string, string> = {}): Promise<{ emails: string[]; count: number }> {
  const response = await apiClient.get<{ emails: string[]; count: number }>("/contacts/emails/", { params })
  return response.data
}

/** Check for duplicates before creating a contact */
export async function checkDuplicates(data: {
  first_name?: string
  last_name?: string
  email?: string
  phone?: string
}): Promise<DuplicateMatch[]> {
  const response = await apiClient.post<DuplicateMatch[]>("/contacts/duplicates/check/", data)
  return response.data
}

/** Scan all contacts for duplicate pairs */
export async function scanDuplicates(): Promise<DuplicatePair[]> {
  const response = await apiClient.get<DuplicatePair[]>("/contacts/duplicates/scan/")
  return response.data
}

/** Merge two contacts */
export async function mergeContacts(data: MergeRequest): Promise<ContactDetail> {
  const response = await apiClient.post<ContactDetail>("/contacts/duplicates/merge/", data)
  return response.data
}

/** Dismiss a duplicate pair */
export async function dismissDuplicate(data: DismissRequest): Promise<void> {
  await apiClient.post("/contacts/duplicates/dismiss/", data)
}
