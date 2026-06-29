import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Loader2, ShieldCheck, CheckCircle } from "lucide-react"
import { useGoalData, useUpdateGoal } from "@/hooks/useGoal"
import { GoalProgressBar } from "@/components/goal/GoalProgressBar"
import { useJournals } from "@/hooks/useJournals"
import { useAuth } from "@/providers/AuthProvider"
import { useViewAs } from "@/providers/ViewAsProvider"
import { computePacingTargets } from "@/lib/pacing"

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MILESTONE_MESSAGES: Record<number, string> = {
  0:   "Every journey starts with a first step — you've got this!",
  25:  "You're a quarter of the way there. Keep making those calls!",
  50:  "Halfway home! Your faithfulness is making a real difference.",
  75:  "Almost there — the finish line is in sight. Keep pressing in!",
  100: "Goal reached! Thank you for your faithful support-raising.",
}

function getMilestoneMessage(pct: number): string {
  if (pct >= 100) return MILESTONE_MESSAGES[100]
  if (pct >= 75)  return MILESTONE_MESSAGES[75]
  if (pct >= 50)  return MILESTONE_MESSAGES[50]
  if (pct >= 25)  return MILESTONE_MESSAGES[25]
  return MILESTONE_MESSAGES[0]
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
})

function formatCurrency(dollars: number): string {
  return currencyFormatter.format(dollars)
}

// ---------------------------------------------------------------------------
// GoalPage
// ---------------------------------------------------------------------------

export default function GoalPage() {
  const { data: goalData, isLoading } = useGoalData()
  const updateGoal = useUpdateGoal()
  const { user } = useAuth()
  const { isViewingAs } = useViewAs()
  const isReadOnly = isViewingAs

  // Goal Settings local state
  const [goalDollars, setGoalDollars] = useState("")
  const [goalWeeks, setGoalWeeks] = useState("")
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [settingsSaved, setSettingsSaved] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  // Fetch only journals owned by the current user
  const journalParams: Record<string, string> = { page_size: "100" }
  if (user?.id) journalParams.owner = user.id
  const { data: journalsData } = useJournals(journalParams)
  const journals = journalsData?.results ?? []

  // Sync local state from API data when it loads
  useEffect(() => {
    if (goalData) {
      setGoalDollars(String(goalData.monthly_support_goal_cents / 100))
      setGoalWeeks(String(goalData.goal_weeks))
      setSelectedIds(new Set(goalData.selected_journal_ids))
    }
  }, [goalData])

  // ---------------------------------------------------------------------------
  // Progress computations
  // ---------------------------------------------------------------------------

  const goalCents = goalData?.monthly_support_goal_cents ?? 0

  const supportPct = goalCents > 0 && goalData
    ? Math.round((goalData.effective_monthly_support / (goalCents / 100)) * 100)
    : 0

  const { callsNeeded, meetingsNeeded } = computePacingTargets(goalCents, goalData?.goal_weeks ?? 0)
  const callsPct = callsNeeded > 0 ? Math.round(((goalData?.calls_count ?? 0) / callsNeeded) * 100) : 0
  const meetingsPct = meetingsNeeded > 0 ? Math.round(((goalData?.meetings_count ?? 0) / meetingsNeeded) * 100) : 0

  const decisionsPct = goalData && goalData.decisions_goal > 0
    ? Math.round((goalData.decisions_current / goalData.decisions_goal) * 100)
    : 0

  // The Monthly Support row is only empty when no goal amount is set. With a
  // goal but no journals, it now shows real all-donor support (ADR 0004), so
  // "no_journals" is no longer a support-row empty state.
  const emptyState = !goalData?.monthly_support_goal_cents ? "no_goal" : null

  // Calls/Meetings/Decisions are inherently journal-based. With no journals
  // selected they have no all-donor equivalent, so the whole journal-activity
  // section is hidden rather than shown as dead "select journals above" rows.
  const hasJournalSelection = (goalData?.selected_journal_ids.length ?? 0) > 0

  // Decisions-specific empty state: has main goal + journals but no journal goals set
  const noJournalGoals = !emptyState && hasJournalSelection && goalData && goalData.decisions_goal === 0

  // ---------------------------------------------------------------------------
  // Save handler
  // ---------------------------------------------------------------------------

  function handleSaveSettings() {
    setValidationError(null)

    // When journals are checked, the Monthly Goal is derived from them: sum the
    // checked journals' monthly goal_amounts and overwrite whatever was typed.
    // With no journals checked, keep the manually entered value (all-donor mode,
    // ADR 0004). goal_amount is a monthly figure (ADR 0008).
    const checkedJournals = journals.filter((j) => selectedIds.has(j.id))
    const hasCheckedJournals = checkedJournals.length > 0

    // Sum exactly in integer cents to avoid float drift: convert each journal's
    // dollar amount to cents first, then add the integers.
    const summedCents = checkedJournals.reduce((total, j) => {
      const journalCents = Math.round(parseFloat(j.goal_amount) * 100)
      return Number.isNaN(journalCents) ? total : total + journalCents
    }, 0)

    const cents = hasCheckedJournals
      ? summedCents
      : Math.round(parseFloat(goalDollars) * 100)
    if (isNaN(cents) || cents < 0) {
      setValidationError("Please enter a valid goal amount.")
      return
    }
    const weeks = parseInt(goalWeeks, 10)
    if (!Number.isInteger(weeks) || weeks <= 0) {
      setValidationError("Please enter a valid number of weeks (must be at least 1).")
      return
    }

    // Reflect the summed total back into the visible input so the user sees the
    // overwrite immediately.
    if (hasCheckedJournals) {
      setGoalDollars(String(cents / 100))
    }

    updateGoal.mutate(
      {
        monthly_support_goal_cents: cents,
        goal_weeks: weeks,
        journal_ids: [...selectedIds],
      },
      {
        onSuccess: () => {
          setSettingsSaved(true)
          setTimeout(() => setSettingsSaved(false), 3000)
        },
      }
    )
  }

  function handleJournalToggle(journalId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(journalId)) {
        next.delete(journalId)
      } else {
        next.add(journalId)
      }
      return next
    })
  }

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-6">
      <h1 className="text-2xl font-bold">Support Goal</h1>

      {/* Read-only banner */}
      {isReadOnly && (
        <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
          <ShieldCheck className="h-4 w-4" />
          You are viewing this page in read-only mode
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Goal Settings Card                                                  */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Goal Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Monthly Goal */}
          <div className="space-y-1">
            <Label htmlFor="monthly-goal">Monthly Goal ($)</Label>
            <Input
              id="monthly-goal"
              type="number"
              min="0"
              step="1"
              placeholder="3500"
              value={goalDollars}
              onChange={(e) => setGoalDollars(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  // Save on Enter, identical to clicking "Save Settings".
                  // preventDefault keeps it explicit/safe even though this
                  // input is not inside a <form>.
                  e.preventDefault()
                  if (!isReadOnly && !updateGoal.isPending) {
                    handleSaveSettings()
                  }
                }
              }}
              disabled={isReadOnly}
            />
          </div>

          {/* Goal Weeks */}
          <div className="space-y-1">
            <Label htmlFor="goal-weeks">Goal Weeks</Label>
            <Input
              id="goal-weeks"
              type="number"
              min="1"
              step="1"
              placeholder="52"
              value={goalWeeks}
              onChange={(e) => setGoalWeeks(e.target.value)}
              disabled={isReadOnly}
            />
          </div>

          {/* Journal checkbox list */}
          {journals.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Track Progress By Journals</p>
              {journals.map((journal) => (
                <div key={journal.id} className="flex items-center gap-2">
                  <Checkbox
                    id={`journal-${journal.id}`}
                    checked={selectedIds.has(journal.id)}
                    onCheckedChange={() => handleJournalToggle(journal.id)}
                    disabled={isReadOnly}
                  />
                  <Label htmlFor={`journal-${journal.id}`} className="cursor-pointer font-normal">
                    {journal.name}
                  </Label>
                </div>
              ))}
            </div>
          )}

          {/* Validation error */}
          {validationError && (
            <p className="text-sm text-destructive">{validationError}</p>
          )}

          {/* Save button (hidden for read-only users) */}
          {!isReadOnly && (
            <div className="flex items-center gap-3">
              <Button onClick={handleSaveSettings} disabled={updateGoal.isPending}>
                {updateGoal.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Save Settings
              </Button>
              {settingsSaved && (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Saved
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* Progress Card                                                       */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Row 1 — Monthly Support */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Monthly Support</span>
              <span className="text-muted-foreground tabular-nums">
                {goalData
                  ? `${formatCurrency(goalData.effective_monthly_support)} / ${formatCurrency(goalData.monthly_support_goal_cents / 100)}`
                  : "— / —"}
              </span>
            </div>
            <GoalProgressBar
              value={supportPct}
              colorVariant="support"
              disabled={!!emptyState}
              label="Monthly support progress"
            />
            {!emptyState && (
              <p className="text-xs text-muted-foreground">{getMilestoneMessage(supportPct)}</p>
            )}
            {!emptyState && !hasJournalSelection && journals.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Showing all your donors. Select journals above to scope this to a campaign.
              </p>
            )}
            {emptyState === "no_goal" && (
              <p className="text-xs text-muted-foreground">
                Set a goal amount above to see your support progress
              </p>
            )}
          </div>

          {/* Rows 2–4 (Calls / Meetings / Decisions) are journal-based and only
              render once journals are selected. See ADR 0004. */}
          {hasJournalSelection && (
          <>
          {/* Row 2 — Calls */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Calls</span>
              <span className="text-muted-foreground tabular-nums">
                {goalData && callsNeeded > 0 ? `${goalData.calls_count} / ${callsNeeded}` : "— / —"}
              </span>
            </div>
            <GoalProgressBar
              value={callsPct}
              disabled={!!emptyState}
              label="Calls progress"
            />
            {emptyState === "no_goal" && (
              <p className="text-xs text-muted-foreground">
                Set a goal amount above to see your calls progress
              </p>
            )}
          </div>

          {/* Row 3 — Meetings */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Meetings</span>
              <span className="text-muted-foreground tabular-nums">
                {goalData && meetingsNeeded > 0 ? `${goalData.meetings_count} / ${meetingsNeeded}` : "— / —"}
              </span>
            </div>
            <GoalProgressBar
              value={meetingsPct}
              disabled={!!emptyState}
              label="Meetings progress"
            />
            {emptyState === "no_goal" && (
              <p className="text-xs text-muted-foreground">
                Set a goal amount above to see your meetings progress
              </p>
            )}
          </div>

          {/* Row 4 — Decisions */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Decisions</span>
              <span className="text-muted-foreground tabular-nums">
                {goalData && goalData.decisions_goal > 0
                  ? `${formatCurrency(goalData.decisions_current)} / ${formatCurrency(goalData.decisions_goal)}`
                  : "-- / --"}
              </span>
            </div>
            <GoalProgressBar
              value={decisionsPct}
              disabled={!!emptyState || !!noJournalGoals}
              label="Decisions progress"
            />
            {emptyState === "no_goal" && (
              <p className="text-xs text-muted-foreground">
                Set a goal amount above to see your decisions progress
              </p>
            )}
            {noJournalGoals && (
              <p className="text-xs text-muted-foreground">
                Set goal amounts on your journals to track decision progress
              </p>
            )}
          </div>
          </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
