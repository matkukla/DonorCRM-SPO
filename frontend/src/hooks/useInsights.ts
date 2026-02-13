import { useQuery } from "@tanstack/react-query"
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
  type StalledContactsParams,
  type TeamActivityParams,
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

export function useAdminDashboardOverview() {
  return useQuery({
    queryKey: ["insights", "admin", "dashboard"],
    queryFn: getAdminDashboardOverview,
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

export function useAdminConversionFunnel() {
  return useQuery({
    queryKey: ["insights", "admin", "conversion-funnel"],
    queryFn: getAdminConversionFunnel,
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
