import { apiClient } from "./client"

export type ContactStatus = "prospect" | "donor" | "lapsed" | "major_donor" | "deceased"

export interface ContactListItem {
  id: string
  first_name: string
  last_name: string
  full_name: string
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
  groups: Array<{ id: string; name: string; description: string | null }>
  created_at: string
  updated_at: string
}

export interface ContactCreate {
  first_name: string
  last_name: string
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

export interface ContactFilters {
  search?: string
  status?: ContactStatus
  needs_thank_you?: boolean
  group?: string
  owner?: string
  ordering?: string
  page?: number
  page_size?: number
}

/**
 * List contacts with optional filters
 */
export async function getContacts(filters: ContactFilters = {}): Promise<PaginatedResponse<ContactListItem>> {
  const params = new URLSearchParams()

  if (filters.search) params.append("search", filters.search)
  if (filters.status) params.append("status", filters.status)
  if (filters.needs_thank_you !== undefined) params.append("needs_thank_you", String(filters.needs_thank_you))
  if (filters.group) params.append("group", filters.group)
  if (filters.owner) params.append("owner", filters.owner)
  if (filters.ordering) params.append("ordering", filters.ordering)
  if (filters.page) params.append("page", String(filters.page))
  if (filters.page_size) params.append("page_size", String(filters.page_size))

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
