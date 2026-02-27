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

// Admin Analytics Types and Functions

export interface DonationSummary {
  total_amount: number
  total_count: number
}

export interface DashboardOverviewParams {
  date_from?: string
  date_to?: string
}

export interface DashboardOverviewResponse {
  total_contacts: number
  active_journals: number
  stalled_contacts: number
  conversion_rate: number
  donations_12m: DonationSummary
}

export interface StalledContactItem {
  id: string
  full_name: string
  email: string | null
  owner_email: string
  owner_name: string
  last_activity_date: string | null
  days_stalled: number | null
  status: string
}

export interface StalledContactsParams {
  limit?: number
  offset?: number
  sort_by?: string
  sort_dir?: string
  date_from?: string
  date_to?: string
}

export interface StalledContactsResponse {
  stalled_contacts: StalledContactItem[]
  total_count: number
  limit: number
  offset: number
}

export interface UserPerformanceItem {
  id: string
  email: string
  name: string
  role: string
  total_contacts: number
  active_journals: number
  decisions_logged: number
  conversion_rate: number
  total_donations: number
  donation_count: number
}

export interface UserPerformanceResponse {
  users: UserPerformanceItem[]
}

export interface FunnelStage {
  stage: string | null
  label: string
  count: number
  percentage: number
}

export interface ConversionFunnelResponse {
  funnel: FunnelStage[]
  total_contacts_in_pipeline: number
}

export interface TeamActivityItem {
  id: string
  user_id: string
  user_email: string
  user_name: string
  event_type: string
  title: string
  message: string
  severity: string
  contact_id: string | null
  contact_name: string | null
  created_at: string
}

export interface TeamActivityParams {
  limit?: number
  date_from?: string
  date_to?: string
}

export interface TeamActivityResponse {
  activities: TeamActivityItem[]
  total_count: number
}

/**
 * Get admin dashboard overview metrics
 */
export async function getAdminDashboardOverview(params?: DashboardOverviewParams): Promise<DashboardOverviewResponse> {
  const response = await apiClient.get<DashboardOverviewResponse>("/insights/admin/dashboard-overview/", {
    params,
  })
  return response.data
}

/**
 * Get admin stalled contacts list
 */
export async function getAdminStalledContacts(params?: StalledContactsParams): Promise<StalledContactsResponse> {
  const response = await apiClient.get<StalledContactsResponse>("/insights/admin/stalled-contacts/", {
    params,
  })
  return response.data
}

/**
 * Get admin user performance metrics
 */
export async function getAdminUserPerformance(): Promise<UserPerformanceResponse> {
  const response = await apiClient.get<UserPerformanceResponse>("/insights/admin/user-performance/")
  return response.data
}

/**
 * Get admin conversion funnel visualization data
 */
export async function getAdminConversionFunnel(params?: ConversionFunnelParams): Promise<ConversionFunnelResponse> {
  const response = await apiClient.get<ConversionFunnelResponse>("/insights/admin/conversion-funnel/", {
    params,
  })
  return response.data
}

/**
 * Get admin team activity feed
 */
export async function getAdminTeamActivity(params?: TeamActivityParams): Promise<TeamActivityResponse> {
  const response = await apiClient.get<TeamActivityResponse>("/insights/admin/team-activity/", {
    params,
  })
  return response.data
}

export interface TrendDataPoint {
  week_start: string
  week_label: string
  decisions_logged: number
  donations_received: number
  stage_progressions: number
}

export interface TeamTrendsResponse {
  trends: TrendDataPoint[]
  weeks: number
}

export interface TeamTrendsParams {
  weeks?: number
  date_from?: string
  date_to?: string
}

export interface ConversionFunnelParams {
  date_from?: string
  date_to?: string
}

/**
 * Get admin team trends (weekly metrics over time)
 */
export async function getAdminTeamTrends(params?: TeamTrendsParams): Promise<TeamTrendsResponse> {
  const response = await apiClient.get<TeamTrendsResponse>("/insights/admin/team-trends/", {
    params,
  })
  return response.data
}

// User Detail Types (Phase 17)

export interface UserTrendsParams {
  user_id: string
  weeks?: number
}

export interface UserTrendsResponse {
  trends: TrendDataPoint[]  // Reuse existing TrendDataPoint interface
  weeks: number
}

export interface UserJournalItem {
  id: string
  name: string
  member_count: number
  decision_count: number
  active_member_count: number
  created_at: string
}

export interface UserJournalsResponse {
  journals: UserJournalItem[]
}

export async function getAdminUserTrends(params: UserTrendsParams): Promise<UserTrendsResponse> {
  const response = await apiClient.get<UserTrendsResponse>("/insights/admin/user-trends/", { params })
  return response.data
}

export async function getAdminUserJournals(params: { user_id: string }): Promise<UserJournalsResponse> {
  const response = await apiClient.get<UserJournalsResponse>("/insights/admin/user-journals/", { params })
  return response.data
}

// Stage Contacts Types (Phase 18)

export interface StageContactItem {
  id: string
  full_name: string
  email: string | null
  owner_name: string
  last_activity_date: string | null
}

export interface StageContactsResponse {
  contacts: StageContactItem[]
  total_count: number
  stage: string
}

export interface StageContactsParams {
  stage: string
  limit?: number
}

export async function getAdminStageContacts(params: StageContactsParams): Promise<StageContactsResponse> {
  const response = await apiClient.get<StageContactsResponse>("/insights/admin/stage-contacts/", { params })
  return response.data
}

// User Drilldown Types (Phase 18)

export interface UserDrilldownJournal {
  id: string
  name: string
  member_count: number
  decision_count: number
  active_member_count: number
  created_at: string
}

export interface UserDrilldownStats {
  total_contacts: number
  active_journals: number
  decisions_logged: number
  conversion_rate: number
  total_donations: number
  donation_count: number
  stalled_contacts: number
}

export interface UserDrilldownResponse {
  user: {
    id: string
    name: string
    email: string
    role: string
  }
  stats: UserDrilldownStats
  journals: UserDrilldownJournal[]
}

export interface UserDrilldownParams {
  user_id: string
}

export async function getAdminUserDrilldown(params: UserDrilldownParams): Promise<UserDrilldownResponse> {
  const response = await apiClient.get<UserDrilldownResponse>("/insights/admin/user-drilldown/", { params })
  return response.data
}

// CSV Export Functions (Phase 19)

/**
 * Export stalled contacts to CSV file
 */
export async function exportStalledContactsCSV(params?: {
  date_from?: string
  date_to?: string
  sort_by?: string
  sort_dir?: string
}): Promise<void> {
  const response = await apiClient.get("/insights/admin/stalled-contacts/export/", {
    params,
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const dateStr = params?.date_from && params?.date_to
    ? `${params.date_from}_to_${params.date_to}`
    : new Date().toISOString().split('T')[0]
  link.download = `stalled_contacts_${dateStr}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Export team activity to CSV file
 */
export async function exportTeamActivityCSV(params?: {
  date_from?: string
  date_to?: string
}): Promise<void> {
  const response = await apiClient.get("/insights/admin/team-activity/export/", {
    params,
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const dateStr = params?.date_from && params?.date_to
    ? `${params.date_from}_to_${params.date_to}`
    : new Date().toISOString().split('T')[0]
  link.download = `team_activity_${dateStr}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
