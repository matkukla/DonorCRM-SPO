/**
 * Pacing target calculations based on GOAL-05:
 * 25 calls and 10 meetings per $1,000 of monthly goal.
 */

export interface PacingTargets {
  callsNeeded: number
  meetingsNeeded: number
  callsPerWeek: number
  meetingsPerWeek: number
}

export function computePacingTargets(goalCents: number, goalWeeks: number): PacingTargets {
  const goalDollars = goalCents / 100
  const callsNeeded = goalDollars > 0 ? Math.ceil((goalDollars / 1000) * 25) : 0
  const meetingsNeeded = goalDollars > 0 ? Math.ceil((goalDollars / 1000) * 10) : 0
  const callsPerWeek = goalWeeks > 0 && callsNeeded > 0 ? Math.ceil(callsNeeded / goalWeeks) : 0
  const meetingsPerWeek = goalWeeks > 0 && meetingsNeeded > 0 ? Math.ceil(meetingsNeeded / goalWeeks) : 0
  return { callsNeeded, meetingsNeeded, callsPerWeek, meetingsPerWeek }
}
