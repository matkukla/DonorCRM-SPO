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
  in_journal: boolean
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
    thank_you_needed: ThankYouContact[]
    thank_you_needed_count: number
  }
  late_donations: LateDonation[]
  late_donations_count: number
  thank_you_queue: ThankYouContact[]
  thank_you_count: number
  support_progress: SupportProgress
  recent_gifts: RecentGift[]
  journal_activity: JournalActivityItem[]
}

export interface JournalActivityItem {
  id: string
  event_type: string
  stage: string
  notes: string
  created_at: string
  contact_name: string
  contact_id: string
  journal_name: string
  journal_id: string
}

export interface DashboardStats {
  total_contacts: number
  donations_this_month: number
  active_pledges: number
  overdue_tasks: number
}

/**
 * Get complete dashboard summary
 */
export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiClient.get<DashboardSummary>("/dashboard/")
  return response.data
}

/**
 * Get basic stats (contacts count, donations this month, etc.)
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  // Fetch from multiple endpoints to get stats
  const [contactsRes, donationsRes, pledgesRes, tasksRes] = await Promise.all([
    apiClient.get("/contacts/", { params: { page_size: 1 } }),
    apiClient.get("/donations/", { params: { page_size: 1 } }),
    apiClient.get("/pledges/", { params: { page_size: 1, status: "active" } }),
    apiClient.get("/tasks/", { params: { page_size: 1, status: "pending" } }),
  ])

  return {
    total_contacts: contactsRes.data.count || 0,
    donations_this_month: donationsRes.data.count || 0,
    active_pledges: pledgesRes.data.count || 0,
    overdue_tasks: tasksRes.data.count || 0,
  }
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
