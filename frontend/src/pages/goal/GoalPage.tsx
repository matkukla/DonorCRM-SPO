import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Loader2, ShieldCheck, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useGoalData, useUpdateGoal } from "@/hooks/useGoal"
import { GoalProgressBar } from "@/components/goal/GoalProgressBar"
import { useJournals } from "@/hooks/useJournals"

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PACING_CONFIG = {
  AVG_GIFT_AMOUNT: 80,       // $80/month default gift per partner
  CALLS_PER_PARTNER: 9,      // call attempts per potential partner
  CONVOS_PER_PARTNER: 3,     // connected conversations per partner (Bar 2 target)
  APPTS_PER_PARTNER: 1.5,    // appointments per partner (Bar 3 target)
} as const

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
// PacingTile sub-component
// ---------------------------------------------------------------------------

function PacingTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// GoalPage
// ---------------------------------------------------------------------------

export default function GoalPage() {
  const { data: goalData, isLoading } = useGoalData()
  const updateGoal = useUpdateGoal()
  const isReadOnly = false // TODO(phase-52): re-enable when View As context exists

  // Goal Settings local state
  const [goalDollars, setGoalDollars] = useState("")
  const [goalWeeks, setGoalWeeks] = useState("")
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [settingsSaved, setSettingsSaved] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  // Fetch journals for checkbox list
  const { data: journalsData } = useJournals({ page_size: "100" })
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
  // Pacing computations (shared by Progress card and Pacing Targets card)
  // ---------------------------------------------------------------------------

  const goalCents = goalData?.monthly_support_goal_cents ?? 0
  const goalDollarsNum = goalCents / 100
  const pacingDisabled = goalCents === 0

  const partnersNeeded = pacingDisabled ? null : Math.ceil(goalDollarsNum / PACING_CONFIG.AVG_GIFT_AMOUNT)
  const callsNeeded    = partnersNeeded !== null ? Math.round(partnersNeeded * PACING_CONFIG.CALLS_PER_PARTNER) : null
  const convosNeeded   = partnersNeeded !== null ? Math.round(partnersNeeded * PACING_CONFIG.CONVOS_PER_PARTNER) : null
  const apptsNeeded    = partnersNeeded !== null ? Math.round(partnersNeeded * PACING_CONFIG.APPTS_PER_PARTNER) : null
  const apptsPerWeek   = (apptsNeeded !== null && (goalData?.goal_weeks ?? 0) > 0)
    ? Math.ceil(apptsNeeded / goalData!.goal_weeks)
    : null

  const fmt = (val: number | null) => val !== null ? String(val) : "—"

  // ---------------------------------------------------------------------------
  // Progress computations
  // ---------------------------------------------------------------------------

  const supportPct = goalCents > 0 && goalData
    ? Math.round((goalData.effective_monthly_support / (goalCents / 100)) * 100)
    : 0

  const emptyState = !goalData?.monthly_support_goal_cents
    ? "no_goal"
    : goalData.selected_journal_ids.length === 0
      ? "no_journals"
      : null

  // ---------------------------------------------------------------------------
  // Save handler
  // ---------------------------------------------------------------------------

  function handleSaveSettings() {
    setValidationError(null)
    const cents = Math.round(parseFloat(goalDollars) * 100)
    if (isNaN(cents) || cents < 0) {
      setValidationError("Please enter a valid goal amount.")
      return
    }
    const weeks = parseInt(goalWeeks, 10)
    if (!Number.isInteger(weeks) || weeks <= 0) {
      setValidationError("Please enter a valid number of weeks (must be at least 1).")
      return
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
            {emptyState === "no_goal" && (
              <p className="text-xs text-muted-foreground">
                Set a goal amount above to see your support progress
              </p>
            )}
            {emptyState === "no_journals" && (
              <p className="text-xs text-muted-foreground">
                Select journals above to see your support progress
              </p>
            )}
          </div>

          {/* Row 2 — Calls / Convos (read-only count from server) */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Calls / Convos</span>
              <span className="text-muted-foreground tabular-nums">
                {goalData?.calls_count ?? 0} / {convosNeeded !== null ? convosNeeded : "—"}
              </span>
            </div>
            <GoalProgressBar
              value={convosNeeded ? Math.round(((goalData?.calls_count ?? 0) / convosNeeded) * 100) : 0}
              disabled={!goalData?.monthly_support_goal_cents}
              label="Calls and conversations progress"
            />
          </div>

          {/* Row 3 — Appointments (read-only count from server) */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm font-medium">
              <span>Appointments</span>
              <span className="text-muted-foreground tabular-nums">
                {goalData?.meetings_count ?? 0} / {apptsNeeded !== null ? apptsNeeded : "—"}
              </span>
            </div>
            <GoalProgressBar
              value={apptsNeeded ? Math.round(((goalData?.meetings_count ?? 0) / apptsNeeded) * 100) : 0}
              disabled={!goalData?.monthly_support_goal_cents}
              label="Appointments progress"
            />
          </div>
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* Pacing Targets Card                                                 */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Pacing Targets</CardTitle>
        </CardHeader>
        <CardContent className={cn(pacingDisabled && "opacity-40 pointer-events-none")}>
          <div className="grid gap-4 sm:grid-cols-2">
            <PacingTile label="Partners Needed" value={fmt(partnersNeeded)} />
            <PacingTile label="Calls Needed" value={fmt(callsNeeded)} />
            <PacingTile label="Appointments Needed" value={fmt(apptsNeeded)} />
            <PacingTile label="Appointments / Week" value={fmt(apptsPerWeek)} />
          </div>
          {pacingDisabled ? (
            <p className="text-xs text-muted-foreground mt-3">
              Set a goal amount above to see pacing targets
            </p>
          ) : (
            <p className="text-xs text-muted-foreground mt-3">
              Based on your {formatCurrency(goalDollarsNum)} goal, we estimate you need about{" "}
              {fmt(partnersNeeded)} mission partners, which means approximately {fmt(callsNeeded)}{" "}
              calls and {fmt(apptsNeeded)} appointments.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
