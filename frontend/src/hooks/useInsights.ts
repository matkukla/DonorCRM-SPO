import { useQuery, useMutation } from "@tanstack/react-query"
import {
  getDonationsByMonth,
  getDonationsByYear,
  getFollowUps,
  getLateDonations,
  getMonthlyCommitments,
  getReviewQueue,
  getTransactions,
  getAdminDashboardOverview,
  getAdminStalledContacts,
  getAdminUserPerformance,
  getAdminConversionFunnel,
  getAdminTeamActivity,
  getAdminTeamTrends,
  getAdminUserTrends,
  getAdminUserJournals,
  getAdminStageContacts,
  getAdminUserDrilldown,
  getAdminActivityHeatmap,
  exportStalledContactsCSV,
  exportTeamActivityCSV,
  type StalledContactsParams,
  type TeamActivityParams,
  type TeamTrendsParams,
  type DashboardOverviewParams,
  type ConversionFunnelParams,
  type ActivityHeatmapParams,
} from "@/api/insights"

const STALE_TIME = 5 * 60 * 1000 // 5 minutes

export function useDonationsByMonth(year?: number) {
  return useQuery({
    queryKey: ["insights", "donations-by-month", year],
    queryFn: () => getDonationsByMonth(year),
    staleTime: STALE_TIME,
  })
}

export function useDonationsByYear(years = 5) {
  return useQuery({
    queryKey: ["insights", "donations-by-year", years],
    queryFn: () => getDonationsByYear(years),
    staleTime: STALE_TIME,
  })
}

export function useMonthlyCommitments() {
  return useQuery({
    queryKey: ["insights", "monthly-commitments"],
    queryFn: getMonthlyCommitments,
    staleTime: STALE_TIME,
  })
}

export function useLateDonations(limit = 50) {
  return useQuery({
    queryKey: ["insights", "late-donations", limit],
    queryFn: () => getLateDonations(limit),
    staleTime: STALE_TIME,
  })
}

export function useFollowUps(limit = 50) {
  return useQuery({
    queryKey: ["insights", "follow-ups", limit],
    queryFn: () => getFollowUps(limit),
    staleTime: STALE_TIME,
  })
}

export function useReviewQueue() {
  return useQuery({
    queryKey: ["insights", "review-queue"],
    queryFn: getReviewQueue,
    staleTime: STALE_TIME,
  })
}

export function useTransactions(params?: {
  limit?: number
  offset?: number
  contact_id?: string
  date_from?: string
  date_to?: string
}) {
  return useQuery({
    queryKey: ["insights", "transactions", params],
    queryFn: () => getTransactions(params),
    staleTime: STALE_TIME,
  })
}

// Admin Analytics Hooks

export function useAdminDashboardOverview(params?: DashboardOverviewParams) {
  return useQuery({
    queryKey: ["insights", "admin", "dashboard", params],
    queryFn: () => getAdminDashboardOverview(params),
    staleTime: STALE_TIME,
  })
}

export function useAdminStalledContacts(params?: StalledContactsParams) {
  return useQuery({
    queryKey: ["insights", "admin", "stalled-contacts", params],
    queryFn: () => getAdminStalledContacts(params),
    staleTime: STALE_TIME,
  })
}

export function useAdminUserPerformance() {
  return useQuery({
    queryKey: ["insights", "admin", "user-performance"],
    queryFn: getAdminUserPerformance,
    staleTime: STALE_TIME,
  })
}

export function useAdminConversionFunnel(params?: ConversionFunnelParams) {
  return useQuery({
    queryKey: ["insights", "admin", "conversion-funnel", params],
    queryFn: () => getAdminConversionFunnel(params),
    staleTime: STALE_TIME,
  })
}

export function useAdminTeamActivity(params?: TeamActivityParams) {
  return useQuery({
    queryKey: ["insights", "admin", "team-activity", params],
    queryFn: () => getAdminTeamActivity(params),
    staleTime: STALE_TIME,
  })
}

export function useAdminTeamTrends(params?: TeamTrendsParams) {
  return useQuery({
    queryKey: ["insights", "admin", "team-trends", params],
    queryFn: () => getAdminTeamTrends(params),
    staleTime: STALE_TIME,
  })
}

export function useAdminUserTrends(userId: string, weeks = 12) {
  return useQuery({
    queryKey: ["insights", "admin", "user-trends", userId, weeks],
    queryFn: () => getAdminUserTrends({ user_id: userId, weeks }),
    staleTime: STALE_TIME,
    enabled: !!userId,
  })
}

export function useAdminUserJournals(userId: string) {
  return useQuery({
    queryKey: ["insights", "admin", "user-journals", userId],
    queryFn: () => getAdminUserJournals({ user_id: userId }),
    staleTime: STALE_TIME,
    enabled: !!userId,
  })
}

export function useAdminStageContacts(stage: string | null) {
  return useQuery({
    queryKey: ["insights", "admin", "stage-contacts", stage],
    queryFn: () => getAdminStageContacts({ stage: stage! }),
    staleTime: STALE_TIME,
    enabled: !!stage,
  })
}

export function useAdminUserDrilldown(userId: string | null) {
  return useQuery({
    queryKey: ["insights", "admin", "user-drilldown", userId],
    queryFn: () => getAdminUserDrilldown({ user_id: userId! }),
    staleTime: STALE_TIME,
    enabled: !!userId,
  })
}

export function useAdminActivityHeatmap(params?: ActivityHeatmapParams) {
  return useQuery({
    queryKey: ["insights", "admin", "activity-heatmap", params],
    queryFn: () => getAdminActivityHeatmap(params),
    staleTime: STALE_TIME,
  })
}

// CSV Export Hooks

export function useExportStalledContacts() {
  return useMutation({
    mutationFn: exportStalledContactsCSV,
  })
}

export function useExportTeamActivity() {
  return useMutation({
    mutationFn: exportTeamActivityCSV,
  })
}
