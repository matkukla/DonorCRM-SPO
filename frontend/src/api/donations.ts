import { apiClient } from "./client"
import type { PaginatedResponse } from "./contacts"

export type DonationType = "one_time" | "recurring" | "special"
export type PaymentMethod = "check" | "cash" | "credit_card" | "bank_transfer" | "other"

export interface Donation {
  id: string
  contact: string
  contact_name: string
  pledge: string | null
  pledge_info: {
    id: string
    amount: string
    frequency: string
  } | null
  amount: string
  date: string
  donation_type: DonationType
  payment_method: PaymentMethod
  external_id: string
  thanked: boolean
  thanked_at: string | null
  thanked_by: string | null
  notes: string
  imported_at: string | null
  import_batch: string
  created_at: string
  updated_at: string
}

export interface DonationCreate {
  contact: string
  pledge?: string
  amount: number | string
  date: string
  donation_type?: DonationType
  payment_method?: PaymentMethod
  external_id?: string
  notes?: string
}

export interface DonationUpdate extends Partial<DonationCreate> {
  thanked?: boolean
}

export interface DonationFilters {
  search?: string
  contact?: string
  donation_type?: DonationType
  payment_method?: PaymentMethod
  thanked?: boolean
  date_after?: string
  date_before?: string
  ordering?: string
  page?: number
  page_size?: number
}

export const donationTypeLabels: Record<DonationType, string> = {
  one_time: "One-Time Gift",
  recurring: "Recurring Gift",
  special: "Special Gift",
}

export const paymentMethodLabels: Record<PaymentMethod, string> = {
  check: "Check",
  cash: "Cash",
  credit_card: "Credit Card",
  bank_transfer: "Bank Transfer/ACH",
  other: "Other",
}

/**
 * List donations with optional filters
 */
export async function getDonations(filters: DonationFilters = {}): Promise<PaginatedResponse<Donation>> {
  const params = new URLSearchParams()

  if (filters.search) params.append("search", filters.search)
  if (filters.contact) params.append("contact", filters.contact)
  if (filters.donation_type) params.append("donation_type", filters.donation_type)
  if (filters.payment_method) params.append("payment_method", filters.payment_method)
  if (filters.thanked !== undefined) params.append("thanked", String(filters.thanked))
  if (filters.date_after) params.append("date_after", filters.date_after)
  if (filters.date_before) params.append("date_before", filters.date_before)
  if (filters.ordering) params.append("ordering", filters.ordering)
  if (filters.page) params.append("page", String(filters.page))
  if (filters.page_size) params.append("page_size", String(filters.page_size))

  const response = await apiClient.get<PaginatedResponse<Donation>>("/donations/", { params })
  return response.data
}

/**
 * Get a single donation by ID
 */
export async function getDonation(id: string): Promise<Donation> {
  const response = await apiClient.get<Donation>(`/donations/${id}/`)
  return response.data
}

/**
 * Create a new donation
 */
export async function createDonation(data: DonationCreate): Promise<Donation> {
  const response = await apiClient.post<Donation>("/donations/", data)
  return response.data
}

/**
 * Update a donation
 */
export async function updateDonation(id: string, data: DonationUpdate): Promise<Donation> {
  const response = await apiClient.patch<Donation>(`/donations/${id}/`, data)
  return response.data
}

/**
 * Delete a donation
 */
export async function deleteDonation(id: string): Promise<void> {
  await apiClient.delete(`/donations/${id}/`)
}

/**
 * Mark a donation as thanked
 */
export async function markDonationThanked(id: string): Promise<Donation> {
  const response = await apiClient.post<Donation>(`/donations/${id}/thank/`)
  return response.data
}
