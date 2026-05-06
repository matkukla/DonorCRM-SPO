import { apiClient } from "./client"
import type { PaginatedResponse } from "./contacts"

// --- Types ---

export type FeedbackType = "bug" | "feature" | "other"
export type FeedbackStatus = "new" | "triaged" | "resolved" | "duplicate"

export interface FeedbackEntry {
  id: string
  submitter: string
  submitter_name: string
  submitter_email: string
  type: FeedbackType
  type_display: string
  title: string
  description: string
  status: FeedbackStatus
  status_display: string
  page_url: string
  user_agent: string
  created_at: string
  updated_at: string
}

export interface FeedbackEntryCreate {
  type: FeedbackType
  title: string
  description: string
  page_url?: string
}

export interface FeedbackEntryUpdate {
  status?: FeedbackStatus
}

// --- API functions ---

export async function getFeedbackEntries(
  params: Record<string, string> = {},
): Promise<PaginatedResponse<FeedbackEntry>> {
  const response = await apiClient.get<PaginatedResponse<FeedbackEntry>>(
    "/feedback/",
    { params },
  )
  return response.data
}

export async function getFeedbackEntry(id: string): Promise<FeedbackEntry> {
  const response = await apiClient.get<FeedbackEntry>(`/feedback/${id}/`)
  return response.data
}

export async function createFeedbackEntry(
  data: FeedbackEntryCreate,
): Promise<FeedbackEntry> {
  const response = await apiClient.post<FeedbackEntry>("/feedback/", data)
  return response.data
}

export async function updateFeedbackEntry(
  id: string,
  data: FeedbackEntryUpdate,
): Promise<FeedbackEntry> {
  const response = await apiClient.patch<FeedbackEntry>(`/feedback/${id}/`, data)
  return response.data
}

export async function deleteFeedbackEntry(id: string): Promise<void> {
  await apiClient.delete(`/feedback/${id}/`)
}
