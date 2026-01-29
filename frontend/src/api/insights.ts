import { apiClient } from "./client"

// Donations by Month
export interface DonationByMonthData {
  month: string
  label: string
  short_label: string
  total: number
  count: number
}

export interface DonationsByMonthResponse {
  year: number
  months: DonationByMonthData[]
  year_total: number
  donation_count: number
}

// Donations by Year
export interface DonationByYearData {
  year: number
  total: number
  count: number
}

export interface DonationsByYearResponse {
  years: DonationByYearData[]
  grand_total: number
  total_donations: number
}

// Monthly Commitments
export interface CommitmentPledge {
  id: string
  contact_id: string
  contact_name: string
  amount: number
  frequency: string
  monthly_equivalent: number
  start_date: string
  last_fulfilled_date: string | null
}

export interface FrequencyBreakdown {
  frequency: string
  count: number
  monthly_total: number
}

export interface MonthlyCommitmentsResponse {
  pledges: CommitmentPledge[]
  total_monthly: number
  total_annual: number
  active_count: number
  by_frequency: FrequencyBreakdown[]
}

// Late Donations
export interface LateDonationItem {
  id: string
  contact_id: string
  contact_name: string
  amount: number
  frequency: string
  monthly_equivalent: number
  last_gift_date: string | null
  days_late: number
  next_expected_date: string | null
}

export interface LateDonationsResponse {
  late_donations: LateDonationItem[]
  total_count: number
}

// Follow-ups
export interface FollowUpTask {
  id: string
  title: string
  description: string
  task_type: string
  priority: string
  status: string
  due_date: string
  is_overdue: boolean
  contact_id: string | null
  contact_name: string | null
}

export interface FollowUpsResponse {
  tasks: FollowUpTask[]
  total_count: number
  overdue_count: number
}

// Review Queue
export interface ReviewQueueItem {
  id: string
  type: string
  title: string
  contact_id: string
  contact_name: string
  last_gift_amount: number | null
  last_gift_date: string | null
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[]
  total_count: number
}

// Transactions
export interface TransactionItem {
  id: string
  contact_id: string
  contact_name: string
  amount: number
  date: string
  donation_type: string
  payment_method: string
  pledge_id: string | null
  thanked: boolean
  notes: string
}

export interface TransactionsResponse {
  transactions: TransactionItem[]
  total_count: number
  limit: number
  offset: number
}

/**
 * Get donations by month for a year
 */
export async function getDonationsByMonth(year?: number): Promise<DonationsByMonthResponse> {
  const response = await apiClient.get<DonationsByMonthResponse>("/insights/donations-by-month/", {
    params: year ? { year } : undefined,
  })
  return response.data
}

/**
 * Get donations by year
 */
export async function getDonationsByYear(years = 5): Promise<DonationsByYearResponse> {
  const response = await apiClient.get<DonationsByYearResponse>("/insights/donations-by-year/", {
    params: { years },
  })
  return response.data
}

/**
 * Get monthly commitments (active pledges)
 */
export async function getMonthlyCommitments(): Promise<MonthlyCommitmentsResponse> {
  const response = await apiClient.get<MonthlyCommitmentsResponse>("/insights/monthly-commitments/")
  return response.data
}

/**
 * Get late donations
 */
export async function getLateDonations(limit = 50): Promise<LateDonationsResponse> {
  const response = await apiClient.get<LateDonationsResponse>("/insights/late-donations/", {
    params: { limit },
  })
  return response.data
}

/**
 * Get follow-ups (incomplete tasks)
 */
export async function getFollowUps(limit = 50): Promise<FollowUpsResponse> {
  const response = await apiClient.get<FollowUpsResponse>("/insights/follow-ups/", {
    params: { limit },
  })
  return response.data
}

/**
 * Get review queue (admin only)
 */
export async function getReviewQueue(): Promise<ReviewQueueResponse> {
  const response = await apiClient.get<ReviewQueueResponse>("/insights/review-queue/")
  return response.data
}

/**
 * Get transactions ledger (admin/finance only)
 */
export async function getTransactions(params?: {
  limit?: number
  offset?: number
  contact_id?: string
  date_from?: string
  date_to?: string
}): Promise<TransactionsResponse> {
  const response = await apiClient.get<TransactionsResponse>("/insights/transactions/", {
    params,
  })
  return response.data
}
