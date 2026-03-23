/**
 * Goal API client
 */
import { apiClient } from "./client"

/**
 * Typed shape of GET /api/v1/goals/me/ response.
 * calls_count and meetings_count are READ-ONLY — they are computed server-side
 * from JournalStageEvent records and cannot be patched.
 */
export interface GoalData {
  monthly_support_goal_cents: number  // cents, e.g. 350000 = $3,500
  goal_weeks: number                  // e.g. 52
  selected_journal_ids: string[]      // UUID strings
  effective_monthly_support: number   // dollars (float)
  recurring_monthly: number           // dollars (float)
  one_time_monthly: number            // dollars (float)
  calls_count: number                 // integer, 0+ (read-only, from journal events)
  meetings_count: number              // integer, 0+ (read-only, from journal events)
  decisions_current: number           // dollars (float), monthly-normalized decision sum
  decisions_goal: number              // dollars (float), sum of journal goal_amounts
  decisions_percentage: number        // 0-100+ (float), (current/goal)*100
}

/**
 * Typed shape of PATCH /api/v1/goals/me/ body.
 * All fields are optional (partial update).
 * NOTE: write key is 'journal_ids' (not 'selected_journal_ids').
 * calls_count and meetings_count are NOT included — they are server-computed.
 */
export interface GoalUpdatePayload {
  monthly_support_goal_cents?: number  // cents
  goal_weeks?: number
  journal_ids?: string[]               // NOTE: write key is 'journal_ids' not 'selected_journal_ids'
}

/**
 * Fetch current user's goal data.
 */
export async function getGoal(): Promise<GoalData> {
  const response = await apiClient.get<GoalData>("/goals/me/")
  return response.data
}

/**
 * Partially update current user's goal fields.
 * Returns the updated GoalData so callers can set query cache directly.
 */
export async function updateGoal(payload: GoalUpdatePayload): Promise<GoalData> {
  const response = await apiClient.patch<GoalData>("/goals/me/", payload)
  return response.data
}
