/**
 * React Query hooks for the admin analytics redesign (Issue #49).
 *
 * Staleness mirrors useInsights: 5 minutes fresh, 30-minute gcTime so the
 * data survives panel/drawer open/close in the same session.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  getFiscalYearDonations,
  getFiscalYearPace,
  getMissionariesBehindGoal,
  getOrgSettings,
  getPipelineFunnelConversion,
  getWeeklyEngagement,
  updateOrgSettings,
  type MissionariesBehindGoalParams,
  type OrgSettingsResponse,
  type WeeklyEngagementParams,
} from "@/api/adminAnalytics"

const STALE_TIME = 5 * 60 * 1000
const GC_TIME = 30 * 60 * 1000

export function useFiscalYearPace() {
  return useQuery({
    queryKey: ["admin-analytics", "fiscal-year-pace"],
    queryFn: getFiscalYearPace,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  })
}

export function useMissionariesBehindGoal(params?: MissionariesBehindGoalParams) {
  return useQuery({
    queryKey: ["admin-analytics", "missionaries-behind-goal", params ?? {}],
    queryFn: () => getMissionariesBehindGoal(params),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  })
}

export function usePipelineFunnelConversion() {
  return useQuery({
    queryKey: ["admin-analytics", "pipeline-funnel-conversion"],
    queryFn: getPipelineFunnelConversion,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  })
}

export function useWeeklyEngagement(params?: WeeklyEngagementParams) {
  return useQuery({
    queryKey: ["admin-analytics", "weekly-engagement", params ?? {}],
    queryFn: () => getWeeklyEngagement(params),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  })
}

export function useFiscalYearDonations() {
  return useQuery({
    queryKey: ["admin-analytics", "fiscal-year-donations"],
    queryFn: getFiscalYearDonations,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  })
}

export function useOrgSettings() {
  return useQuery({
    queryKey: ["admin-analytics", "org-settings"],
    queryFn: getOrgSettings,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  })
}

export function useUpdateOrgSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<OrgSettingsResponse>) => updateOrgSettings(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-analytics", "org-settings"] })
      queryClient.invalidateQueries({ queryKey: ["admin-analytics", "fiscal-year-pace"] })
    },
  })
}
