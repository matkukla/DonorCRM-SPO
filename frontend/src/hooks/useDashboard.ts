import { useQuery } from "@tanstack/react-query"
import { getDashboardSummary, getDashboardStats, getGivingSummary, getMonthlyGifts } from "@/api/dashboard"

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useGivingSummary(year?: number) {
  return useQuery({
    queryKey: ["dashboard", "giving-summary", year],
    queryFn: () => getGivingSummary(year),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useMonthlyGifts(months = 12) {
  return useQuery({
    queryKey: ["dashboard", "monthly-gifts", months],
    queryFn: () => getMonthlyGifts(months),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
