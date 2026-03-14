import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { getGoal, updateGoal } from "@/api/goals"
import type { GoalUpdatePayload } from "@/api/goals"

/**
 * Fetch current user's goal data.
 */
export function useGoalData() {
  return useQuery({
    queryKey: ["goal"],
    queryFn: getGoal,
  })
}

/**
 * Mutate current user's goal fields.
 * Sets query data directly from mutation response to avoid a stale-cache
 * round-trip flash — the PATCH response already returns the updated GoalData.
 */
export function useUpdateGoal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: GoalUpdatePayload) => updateGoal(payload),
    onSuccess: (data) => {
      // Set query data directly from mutation response to avoid extra round-trip
      queryClient.setQueryData(["goal"], data)
    },
  })
}
