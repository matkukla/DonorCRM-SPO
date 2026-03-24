import { apiClient } from "./client"
import type { PaginatedResponse } from "./contacts"

// Status and frequency enums for RecurringGift (RE-compatible extended set)
export type RecurringGiftStatus = "active" | "held" | "completed" | "cancelled" | "terminated"
export type RecurringGiftFrequency = "monthly" | "quarterly" | "semi_annually" | "annually" | "bimonthly" | "biweekly" | "weekly" | "irregular"
export type GiftPaymentType = "credit_card" | "direct_deposit" | "check"

export interface Gift {
  id: string
  donor_contact: string
  donor_contact_name: string
  owner_name: string | null
  fund: string | null
  fund_name: string | null
  external_gift_id: string
  amount_cents: number
  amount_dollars: string  // Decimal from serializer
  gift_date: string
  description: string
  payment_type: string
  payment_type_display: string | null
  created_at: string
  updated_at: string
}

export interface GiftCredit {
  id: string
  solicitor: string
  solicitor_name: string
  amount_cents: number
  amount_dollars: string
}

export interface GiftWithCredits extends Gift {
  credits: GiftCredit[]
}

export interface GiftCreate {
  donor_contact: string
  fund?: string
  amount_cents: number
  gift_date: string
  description?: string
  payment_type?: string
  external_gift_id?: string
}

export interface GiftUpdate extends Partial<GiftCreate> {}

export interface RecurringGift {
  id: string
  donor_contact: string
  donor_contact_name: string
  owner_name: string | null
  fund: string | null
  fund_name: string | null
  external_gift_id: string
  amount_cents: number
  amount_dollars: string
  frequency: RecurringGiftFrequency
  start_date: string
  end_date: string | null
  status: RecurringGiftStatus
  monthly_equivalent: string
  description: string
  created_at: string
  updated_at: string
}

export interface RecurringGiftCreate {
  donor_contact: string
  fund?: string
  amount_cents: number
  frequency?: RecurringGiftFrequency
  status?: RecurringGiftStatus
  start_date: string
  end_date?: string
  description?: string
  external_gift_id?: string
}

export interface RecurringGiftUpdate extends Partial<RecurringGiftCreate> {}

// Label maps
export const giftPaymentTypeLabels: Record<string, string> = {
  credit_card: "Credit Card",
  direct_deposit: "Direct Deposit",
  check: "Check",
  cash: "Cash",
  online: "Online",
}

export const recurringGiftStatusLabels: Record<RecurringGiftStatus, string> = {
  active: "Active",
  held: "Held",
  completed: "Completed",
  cancelled: "Cancelled",
  terminated: "Terminated",
}

export const recurringGiftFrequencyLabels: Record<RecurringGiftFrequency, string> = {
  monthly: "Monthly",
  quarterly: "Quarterly",
  semi_annually: "Semi-Annual",
  annually: "Annual",
  bimonthly: "Bi-Monthly",
  biweekly: "Bi-Weekly",
  weekly: "Weekly",
  irregular: "Irregular",
}

// --- Gift API functions (use /donations/ alias path) ---
export async function getGifts(params: Record<string, string> = {}): Promise<PaginatedResponse<Gift>> {
  const response = await apiClient.get<PaginatedResponse<Gift>>("/donations/", { params })
  return response.data
}

export async function getGift(id: string): Promise<GiftWithCredits> {
  const response = await apiClient.get<GiftWithCredits>(`/donations/${id}/`)
  return response.data
}

export async function createGift(data: GiftCreate): Promise<Gift> {
  const response = await apiClient.post<Gift>("/donations/", data)
  return response.data
}

export async function updateGift(id: string, data: GiftUpdate): Promise<Gift> {
  const response = await apiClient.patch<Gift>(`/donations/${id}/`, data)
  return response.data
}

export async function deleteGift(id: string): Promise<void> {
  await apiClient.delete(`/donations/${id}/`)
}

// --- RecurringGift API functions (use /pledges/recurring/ alias path) ---
// /pledges/ is an alias for the gifts app root. So /pledges/recurring/ maps to
// the RecurringGift endpoints. This is consistent with using /donations/ for gifts.
export async function getRecurringGifts(params: Record<string, string> = {}): Promise<PaginatedResponse<RecurringGift>> {
  const response = await apiClient.get<PaginatedResponse<RecurringGift>>("/pledges/recurring/", { params })
  return response.data
}

export async function getRecurringGift(id: string): Promise<RecurringGift> {
  const response = await apiClient.get<RecurringGift>(`/pledges/recurring/${id}/`)
  return response.data
}

export async function createRecurringGift(data: RecurringGiftCreate): Promise<RecurringGift> {
  const response = await apiClient.post<RecurringGift>("/pledges/recurring/", data)
  return response.data
}

export async function updateRecurringGift(id: string, data: RecurringGiftUpdate): Promise<RecurringGift> {
  const response = await apiClient.patch<RecurringGift>(`/pledges/recurring/${id}/`, data)
  return response.data
}

export async function deleteRecurringGift(id: string): Promise<void> {
  await apiClient.delete(`/pledges/recurring/${id}/`)
}
