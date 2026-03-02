import { apiClient } from "./client"
import type { PaginatedResponse } from "./contacts"

// --- Types ---

export type PrayerIntentionStatus = "active" | "answered" | "archived"

export interface PrayerIntention {
  id: string
  contact: string
  contact_name: string
  owner_name: string | null
  title: string
  description: string
  status: PrayerIntentionStatus
  last_prayed_at: string | null
  answered_at: string | null
  archived_at: string | null
  created_at: string
  updated_at: string
}

export interface PrayerIntentionCreate {
  contact: string
  title: string
  description?: string
  status?: PrayerIntentionStatus
}

export interface PrayerIntentionUpdate {
  title?: string
  description?: string
  status?: PrayerIntentionStatus
  contact?: string
}

// --- API functions ---

export async function getPrayers(
  params: Record<string, string> = {},
): Promise<PaginatedResponse<PrayerIntention>> {
  const response = await apiClient.get<PaginatedResponse<PrayerIntention>>("/prayers/", { params })
  return response.data
}

export async function getPrayer(id: string): Promise<PrayerIntention> {
  const response = await apiClient.get<PrayerIntention>(`/prayers/${id}/`)
  return response.data
}

export async function createPrayer(data: PrayerIntentionCreate): Promise<PrayerIntention> {
  const response = await apiClient.post<PrayerIntention>("/prayers/", data)
  return response.data
}

export async function updatePrayer(
  id: string,
  data: PrayerIntentionUpdate,
): Promise<PrayerIntention> {
  const response = await apiClient.patch<PrayerIntention>(`/prayers/${id}/`, data)
  return response.data
}

export async function deletePrayer(id: string): Promise<void> {
  await apiClient.delete(`/prayers/${id}/`)
}

export async function markPrayed(id: string): Promise<{ detail: string }> {
  const response = await apiClient.post<{ detail: string }>(`/prayers/${id}/prayed/`)
  return response.data
}

export async function getTodaysFocus(): Promise<PrayerIntention[]> {
  const response = await apiClient.get<PrayerIntention[]>("/prayers/focus/")
  return response.data
}

export async function getContactPrayers(
  contactId: string,
): Promise<PaginatedResponse<PrayerIntention>> {
  const response = await apiClient.get<PaginatedResponse<PrayerIntention>>(
    `/contacts/${contactId}/prayer-intentions/`,
  )
  return response.data
}
