import * as React from "react"
import { Progress } from "@/components/ui/progress"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Pencil, Check } from "lucide-react"
import { useUpdateJournal } from "@/hooks/useJournals"
import { useViewAs } from "@/providers/ViewAsProvider"
import type { JournalDetail, JournalMember, DecisionSummary } from "@/types/journals"
import { formatLocalDate } from "@/lib/utils"

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
 * Per GH-26:
 * - Goal amount is inline-editable via pencil icon (hidden in View As mode)
 *
 * Stats are memoized to prevent cascade re-renders when individual cells update.
 */
export function JournalHeader({ journal, members }: JournalHeaderProps) {
  const { isViewingAs } = useViewAs()
  const updateJournal = useUpdateJournal()

  // Inline edit state for goal amount
  const [isEditingGoal, setIsEditingGoal] = React.useState(false)
  const [editGoalValue, setEditGoalValue] = React.useState("")

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

  function handleStartEdit() {
    setEditGoalValue(parseFloat(journal.goal_amount).toString())
    setIsEditingGoal(true)
  }

  function handleSaveGoal() {
    const parsed = parseFloat(editGoalValue)
    if (isNaN(parsed) || parsed < 0.01) return
    updateJournal.mutate(
      { id: journal.id, data: { goal_amount: parsed.toFixed(2) } },
      { onSuccess: () => setIsEditingGoal(false) }
    )
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSaveGoal()
    if (e.key === "Escape") setIsEditingGoal(false)
  }

  return (
    <div className="space-y-4 p-4 bg-card rounded-lg border">
      {/* Title and stats row */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{journal.name}</h1>
          <div className="flex items-center gap-1 text-muted-foreground">
            {isEditingGoal ? (
              <span className="flex items-center gap-1">
                <span>Goal: $</span>
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={editGoalValue}
                  onChange={(e) => setEditGoalValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="h-7 w-28 text-sm"
                  autoFocus
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={handleSaveGoal}
                  disabled={updateJournal.isPending}
                >
                  <Check className="h-3.5 w-3.5" />
                </Button>
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <span>
                  Goal: ${parseFloat(journal.goal_amount).toLocaleString()}
                </span>
                {!isViewingAs && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={handleStartEdit}
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                )}
              </span>
            )}
            {journal.deadline && (
              <span> &bull; Due {formatLocalDate(journal.deadline)}</span>
            )}
          </div>
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
