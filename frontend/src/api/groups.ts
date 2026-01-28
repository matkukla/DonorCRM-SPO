/**
 * Groups API client
 */
import { apiClient } from "./client"
import type { ContactListItem } from "./contacts"

// Types
export interface Group {
  id: string
  name: string
  description: string
  color: string
  owner: string | null
  is_system: boolean
  is_shared: boolean
  contact_count: number
  created_at: string
  updated_at: string
}

export interface GroupCreate {
  name: string
  description?: string
  color?: string
}

export interface GroupUpdate {
  name?: string
  description?: string
  color?: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// API functions
export async function getGroups(): Promise<Group[]> {
  const response = await apiClient.get("/groups/")
  // Handle both paginated and non-paginated responses
  if (response.data.results) {
    return response.data.results
  }
  return response.data
}

export async function getGroup(id: string): Promise<Group> {
  const response = await apiClient.get(`/groups/${id}/`)
  return response.data
}

export async function createGroup(data: GroupCreate): Promise<Group> {
  const response = await apiClient.post("/groups/", data)
  return response.data
}

export async function updateGroup(id: string, data: GroupUpdate): Promise<Group> {
  const response = await apiClient.patch(`/groups/${id}/`, data)
  return response.data
}

export async function deleteGroup(id: string): Promise<void> {
  await apiClient.delete(`/groups/${id}/`)
}

// Group contacts management
export async function getGroupContacts(groupId: string): Promise<ContactListItem[]> {
  const response = await apiClient.get(`/groups/${groupId}/contacts/`)
  return response.data
}

export async function addContactsToGroup(groupId: string, contactIds: string[]): Promise<void> {
  await apiClient.post(`/groups/${groupId}/contacts/`, { contact_ids: contactIds })
}

export async function removeContactsFromGroup(groupId: string, contactIds: string[]): Promise<void> {
  await apiClient.delete(`/groups/${groupId}/contacts/`, { data: { contact_ids: contactIds } })
}

/** Get all email addresses for contacts in a group */
export async function getGroupContactEmails(groupId: string): Promise<{ emails: string[]; count: number }> {
  const response = await apiClient.get<{ emails: string[]; count: number }>(`/groups/${groupId}/contacts/emails/`)
  return response.data
}
