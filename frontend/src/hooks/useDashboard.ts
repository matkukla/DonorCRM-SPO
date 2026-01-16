import { useQuery } from "@tanstack/react-query"
import { getDashboardSummary, getDashboardStats } from "@/api/dashboard"

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
