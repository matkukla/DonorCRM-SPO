import * as React from "react"
import { Progress } from "@/components/ui/progress"
import type { JournalDetail, JournalMember, DecisionSummary } from "@/types/journals"

export interface JournalHeaderProps {
  /** Journal details */
  journal: JournalDetail
  /** Journal members for stats calculation */
  members: JournalMember[]
}

/**
 * Journal header displaying name, goal, progress bar, and aggregated stats.
 *
 * Per JRN-14:
 * - Header shows journal name, goal amount, current progress bar
 * - Shows total decisions made (count) and total amount pledged
 * - Shows percentage toward goal
 *
 * Stats are memoized to prevent cascade re-renders when individual cells update.
 */
export function JournalHeader({ journal, members }: JournalHeaderProps) {
  // Calculate stats from cached member data
  // Memoize to prevent re-renders (per Phase 5 success criteria #7)
  const stats = React.useMemo(() => {
    // Filter to non-declined decisions
    const decisions = members
      .map((m) => m.decision)
      .filter((d): d is DecisionSummary => d !== null && d.status !== 'declined')

    // Sum total pledged (raw amounts, not monthly equivalent)
    const totalPledged = decisions.reduce(
      (sum, d) => sum + parseFloat(d.amount),
      0
    )

    // Sum monthly equivalent for recurring view
    const totalMonthly = decisions.reduce(
      (sum, d) => sum + parseFloat(d.monthly_equivalent),
      0
    )

    // Count of decisions made
    const decisionCount = decisions.length

    // Progress toward goal
    const goalAmount = parseFloat(journal.goal_amount)
    const progressPercent = goalAmount > 0
      ? Math.min((totalPledged / goalAmount) * 100, 100)
      : 0

    return { totalPledged, totalMonthly, decisionCount, progressPercent }
  }, [members, journal.goal_amount])

  return (
    <div className="space-y-4 p-4 bg-card rounded-lg border">
      {/* Title and stats row */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{journal.name}</h1>
          <p className="text-muted-foreground">
            Goal: ${parseFloat(journal.goal_amount).toLocaleString()}
            {journal.deadline && (
              <span> &bull; Due {new Date(journal.deadline).toLocaleDateString()}</span>
            )}
          </p>
        </div>
        <div className="text-right text-sm space-y-1">
          <p className="text-muted-foreground">
            {stats.decisionCount} {stats.decisionCount === 1 ? 'decision' : 'decisions'} made
          </p>
          <p className="font-semibold text-lg">
            ${stats.totalPledged.toLocaleString()} pledged
          </p>
          {stats.totalMonthly > 0 && (
            <p className="text-xs text-muted-foreground">
              ${stats.totalMonthly.toLocaleString()}/mo recurring
            </p>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <Progress value={stats.progressPercent} className="h-3" />
        <p className="text-xs text-muted-foreground text-center">
          {stats.progressPercent.toFixed(0)}% of goal
        </p>
      </div>
    </div>
  )
}
