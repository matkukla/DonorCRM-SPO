/**
 * Typed API client for the /admin/analytics redesign (Issue #49).
 *
 * Endpoints live under /api/v1/insights/admin/ (same prefix as the legacy
 * admin insights routes). All are admin-only on the backend.
 */
import { apiClient } from "./client"

// --- Fiscal Year Pace ---------------------------------------------------------

export interface FiscalYearPaceResponse {
  fy_start: string
  fy_end: string
  raised_cents: number
  annual_goal_cents: number
  annual_goal_source: "org_setting" | "missionary_sum"
  expected_by_today_cents: number
  pace_percentage: number
  prior_year_raised_cents: number
  yoy_delta_percentage: number | null
  last_import_at: string | null
}

export async function getFiscalYearPace(): Promise<FiscalYearPaceResponse> {
  const response = await apiClient.get<FiscalYearPaceResponse>(
    "/insights/admin/fiscal-year-pace/",
  )
  return response.data
}

// --- Org Settings -------------------------------------------------------------

export interface OrgSettingsResponse {
  annual_goal_cents: number
}

export async function getOrgSettings(): Promise<OrgSettingsResponse> {
  const response = await apiClient.get<OrgSettingsResponse>(
    "/insights/admin/org-settings/",
  )
  return response.data
}

export async function updateOrgSettings(
  payload: Partial<OrgSettingsResponse>,
): Promise<OrgSettingsResponse> {
  const response = await apiClient.patch<OrgSettingsResponse>(
    "/insights/admin/org-settings/",
    payload,
  )
  return response.data
}

// --- Missionaries Behind Goal -------------------------------------------------

export interface MissionaryBehindGoalItem {
  user_id: string
  name: string
  email: string
  monthly_goal_cents: number
  this_month_raised_cents: number
  pace_percentage: number
}

export interface MissionariesBehindGoalResponse {
  missionaries: MissionaryBehindGoalItem[]
  total_excluded_no_goal: number
  total_missionaries: number
  as_of_date: string
}

export interface MissionariesBehindGoalParams {
  limit?: number
}

export async function getMissionariesBehindGoal(
  params?: MissionariesBehindGoalParams,
): Promise<MissionariesBehindGoalResponse> {
  const response = await apiClient.get<MissionariesBehindGoalResponse>(
    "/insights/admin/missionaries-behind-goal/",
    { params },
  )
  return response.data
}

// --- Pipeline Funnel Conversion -----------------------------------------------

export interface PipelineFunnelConversionStage {
  stage: string
  label: string
  count_at_or_past: number
  conversion_from_prior_percentage: number | null
  is_weakest_transition: boolean
}

export interface PipelineFunnelWeakestTransition {
  from: string
  to: string
  rate: number
}

export interface PipelineFunnelConversionResponse {
  stages: PipelineFunnelConversionStage[]
  total_in_pipeline: number
  weakest_transition: PipelineFunnelWeakestTransition | null
}

export async function getPipelineFunnelConversion(): Promise<PipelineFunnelConversionResponse> {
  const response = await apiClient.get<PipelineFunnelConversionResponse>(
    "/insights/admin/pipeline-funnel-conversion/",
  )
  return response.data
}

// --- Weekly Engagement --------------------------------------------------------

export interface WeeklyEngagementPoint {
  week_start: string
  week_label: string
  active_missionaries: number
  on_pace_missionaries: number
  total_missionaries: number
}

export interface WeeklyEngagementResponse {
  weeks: WeeklyEngagementPoint[]
}

export interface WeeklyEngagementParams {
  weeks?: number
}

export async function getWeeklyEngagement(
  params?: WeeklyEngagementParams,
): Promise<WeeklyEngagementResponse> {
  const response = await apiClient.get<WeeklyEngagementResponse>(
    "/insights/admin/weekly-engagement/",
    { params },
  )
  return response.data
}

// --- Fiscal Year Donations ----------------------------------------------------

export interface FiscalYearDonationMonth {
  month: string
  short_label: string
  current_cents: number | null
  prior_cents: number
  is_future: boolean
}

export interface FiscalYearDonationsResponse {
  fy_start: string
  fy_end: string
  months: FiscalYearDonationMonth[]
  current_fy_total_cents: number
  prior_fy_total_cents: number
}

export async function getFiscalYearDonations(): Promise<FiscalYearDonationsResponse> {
  const response = await apiClient.get<FiscalYearDonationsResponse>(
    "/insights/admin/fiscal-year-donations/",
  )
  return response.data
}
