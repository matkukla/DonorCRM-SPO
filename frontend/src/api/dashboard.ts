import { apiClient } from "./client"

export interface DashboardEvent {
  id: string
  event_type: string
  title: string
  message: string
  severity: string
  created_at: string
  is_read: boolean
}

export interface LatePledge {
  id: string
  amount: string
  frequency: string
  days_late: number
}

export interface OverdueTask {
  id: string
  title: string
  due_date: string
  priority: string
}

export interface ThankYouContact {
  id: string
  first_name: string
  last_name: string
  last_gift_amount: string | null
  last_gift_date: string | null
}

export interface LateDonation {
  id: string
  contact_id: string
  contact_name: string
  amount: string
  frequency: string
  monthly_equivalent: number
  last_gift_date: string | null
  days_late: number
  next_expected_date: string | null
}

export interface RecentGift {
  id: string
  amount: string
  date: string
  contact_id: string
  contact__first_name: string
  contact__last_name: string
}

export interface SupportProgress {
  current_monthly_support: number
  monthly_goal: number
  percentage: number
  gap: number
  active_pledge_count: number
}

export interface DashboardSummary {
  what_changed: {
    event_counts: Record<string, number>
    recent_events: DashboardEvent[]
    total_new: number
  }
  needs_attention: {
    late_pledges: LatePledge[]
    late_pledge_count: number
    overdue_tasks: OverdueTask[]
    overdue_task_count: number
    tasks_due_today: OverdueTask[]
    tasks_due_today_count: number
    broadcast_tasks: OverdueTask[]
    broadcast_task_count: number
    thank_you_needed: ThankYouContact[]
    thank_you_needed_count: number
  }
  late_donations: LateDonation[]
  late_donations_count: number
  thank_you_queue: ThankYouContact[]
  thank_you_count: number
  support_progress: SupportProgress
  recent_gifts_total: number
  recent_gifts: RecentGift[]
}

export interface GivingSummary {
  given: number
  expecting: number
  total: number
  recurring_pledges_annual: number
  recurring_pledges_monthly: number
  annual_goal: number
  monthly_goal: number
  percentage: number
  fiscal_year_label: string
  active_pledge_count: number
  last_import_at: string | null
}

export interface MonthlyGiftData {
  month: string
  label: string
  short_label: string
  total: number
}

export interface MonthlyGiftsResponse {
  months: MonthlyGiftData[]
  monthly_goal: number
}

/**
 * Mark dashboard events as seen (POST).
 * Called after dashboard renders to decouple marking from GET (QAL-09).
 */
export async function markEventsSeen(): Promise<void> {
  await apiClient.post("/dashboard/mark-seen/")
}

/**
 * Get complete dashboard summary
 */
export async function getDashboardSummary(userId?: string): Promise<DashboardSummary> {
  const params = userId ? { user_id: userId } : undefined
  const response = await apiClient.get<DashboardSummary>("/dashboard/", { params })
  return response.data
}

/**
 * Get recent gifts
 */
export async function getRecentGifts(days = 30, limit = 10) {
  const response = await apiClient.get("/dashboard/recent-gifts/", {
    params: { days, limit },
  })
  return response.data
}

/**
 * Get needs attention data
 */
export async function getNeedsAttention() {
  const response = await apiClient.get("/dashboard/needs-attention/")
  return response.data
}

/**
 * Get giving summary (Given & Expecting widget)
 */
export async function getGivingSummary(userId?: string): Promise<GivingSummary> {
  const params: Record<string, string | number> = {}
  if (userId) params.user_id = userId
  const response = await apiClient.get<GivingSummary>("/dashboard/giving-summary/", {
    params: Object.keys(params).length > 0 ? params : undefined,
  })
  return response.data
}

/**
 * Get monthly gift totals for bar chart
 */
export async function getMonthlyGifts(months = 12, userId?: string): Promise<MonthlyGiftsResponse> {
  const params: Record<string, string | number> = { months }
  if (userId) params.user_id = userId
  const response = await apiClient.get<MonthlyGiftsResponse>("/dashboard/monthly-gifts/", {
    params,
  })
  return response.data
}

/**
 * Save dashboard layout preferences to user profile
 */
export async function saveDashboardLayout(tileOrder: string[]): Promise<void> {
  await apiClient.patch("/users/me/", {
    dashboard_layout: { tile_order: tileOrder }
  })
}

/**
 * Get dashboard layout preferences from user profile
 */
export async function getDashboardLayout(): Promise<{ tile_order?: string[] }> {
  const response = await apiClient.get<{ dashboard_layout: { tile_order?: string[] } }>("/users/me/")
  return response.data.dashboard_layout || {}
}

/**
 * Get another user's dashboard layout (for supervisor/admin viewing)
 */
export async function getUserDashboardLayout(userId: string): Promise<{ tile_order?: string[] }> {
  const response = await apiClient.get<{ dashboard_layout: { tile_order?: string[] } }>(
    `/dashboard/user/${userId}/layout/`
  )
  return response.data.dashboard_layout || {}
}
