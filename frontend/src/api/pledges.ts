import { apiClient } from "./client"
import type { PaginatedResponse } from "./contacts"

export type PledgeFrequency = "monthly" | "quarterly" | "semi_annual" | "annual"
export type PledgeStatus = "active" | "paused" | "completed" | "cancelled"

export interface Pledge {
  id: string
  contact: string
  contact_name: string
  amount: string
  frequency: PledgeFrequency
  status: PledgeStatus
  start_date: string
  end_date: string | null
  last_fulfilled_date: string | null
  next_expected_date: string | null
  total_expected: string
  total_received: string
  monthly_equivalent: string
  fulfillment_percentage: number
  is_late: boolean
  days_late: number
  late_notified_at: string | null
  notes: string
  created_at: string
  updated_at: string
}

export interface PledgeCreate {
  contact: string
  amount: number | string
  frequency?: PledgeFrequency
  status?: PledgeStatus
  start_date: string
  end_date?: string
  notes?: string
}

export interface PledgeUpdate extends Partial<PledgeCreate> {}

export interface PledgeFilters {
  contact?: string
  status?: PledgeStatus
  is_late?: boolean
  ordering?: string
  page?: number
  page_size?: number
}

export const pledgeFrequencyLabels: Record<PledgeFrequency, string> = {
  monthly: "Monthly",
  quarterly: "Quarterly",
  semi_annual: "Semi-Annual",
  annual: "Annual",
}

export const pledgeStatusLabels: Record<PledgeStatus, string> = {
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
}

/**
 * List pledges with optional filters
 */
export async function getPledges(params: Record<string, string> = {}): Promise<PaginatedResponse<Pledge>> {
  const response = await apiClient.get<PaginatedResponse<Pledge>>("/pledges/", { params })
  return response.data
}

/**
 * Get a single pledge by ID
 */
export async function getPledge(id: string): Promise<Pledge> {
  const response = await apiClient.get<Pledge>(`/pledges/${id}/`)
  return response.data
}

/**
 * Create a new pledge
 */
export async function createPledge(data: PledgeCreate): Promise<Pledge> {
  const response = await apiClient.post<Pledge>("/pledges/", data)
  return response.data
}

/**
 * Update a pledge
 */
export async function updatePledge(id: string, data: PledgeUpdate): Promise<Pledge> {
  const response = await apiClient.patch<Pledge>(`/pledges/${id}/`, data)
  return response.data
}

/**
 * Delete a pledge
 */
export async function deletePledge(id: string): Promise<void> {
  await apiClient.delete(`/pledges/${id}/`)
}

/**
 * Pause a pledge
 */
export async function pausePledge(id: string): Promise<Pledge> {
  const response = await apiClient.post<Pledge>(`/pledges/${id}/pause/`)
  return response.data
}

/**
 * Resume a pledge
 */
export async function resumePledge(id: string): Promise<Pledge> {
  const response = await apiClient.post<Pledge>(`/pledges/${id}/resume/`)
  return response.data
}

/**
 * Cancel a pledge
 */
export async function cancelPledge(id: string): Promise<Pledge> {
  const response = await apiClient.post<Pledge>(`/pledges/${id}/cancel/`)
  return response.data
}
