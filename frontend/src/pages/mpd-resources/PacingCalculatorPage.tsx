import { Loader2, ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { useGoalData } from "@/hooks/useGoal"
import { useViewAs } from "@/providers/ViewAsProvider"
import { computePacingTargets } from "@/lib/pacing"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function PacingTile({
  label,
  value,
  subtitle,
}: {
  label: string
  value: string
  subtitle?: string
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
        {label}
      </p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// PacingCalculatorPage
// ---------------------------------------------------------------------------

export default function PacingCalculatorPage() {
  const { data: goalData, isLoading } = useGoalData()
  const { isViewingAs } = useViewAs()

  const goalCents = goalData?.monthly_support_goal_cents ?? 0
  const goalDollarsNum = goalCents / 100
  const goalWeeks = goalData?.goal_weeks ?? 0
  const pacingDisabled = goalCents === 0

  const { callsNeeded, meetingsNeeded, callsPerWeek, meetingsPerWeek } =
    computePacingTargets(goalCents, goalWeeks)

  const callsMade = goalData?.calls_count ?? 0
  const meetingsHeld = goalData?.meetings_count ?? 0

  // Loading state
  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-6">
      <h1 className="text-2xl font-bold">Pacing Calculator</h1>

      {/* Read-only banner */}
      {isViewingAs && (
        <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
          <ShieldCheck className="h-4 w-4" />
          You are viewing this page in read-only mode
        </div>
      )}

      {/* Pacing Targets Card */}
      <Card>
        <CardHeader>
          <CardTitle>Pacing Targets</CardTitle>
        </CardHeader>
        <CardContent
          className={cn(pacingDisabled && "opacity-40 pointer-events-none")}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <PacingTile
              label="Calls Needed"
              value={pacingDisabled ? "\u2014" : String(callsNeeded)}
              subtitle={pacingDisabled ? undefined : `${callsMade} made`}
            />
            <PacingTile
              label="Meetings Needed"
              value={pacingDisabled ? "\u2014" : String(meetingsNeeded)}
              subtitle={pacingDisabled ? undefined : `${meetingsHeld} completed`}
            />
            <PacingTile
              label="Calls / Week"
              value={pacingDisabled || callsPerWeek === 0 ? "\u2014" : String(callsPerWeek)}
            />
            <PacingTile
              label="Meetings / Week"
              value={pacingDisabled || meetingsPerWeek === 0 ? "\u2014" : String(meetingsPerWeek)}
            />
          </div>
          {pacingDisabled ? (
            <p className="text-xs text-muted-foreground mt-3">
              Set a goal amount on the Goal page to see pacing targets
            </p>
          ) : (
            <p className="text-xs text-muted-foreground mt-3">
              Based on your {formatCurrency(goalDollarsNum)} goal, you need
              approximately {callsNeeded} calls and {meetingsNeeded} meetings{goalWeeks > 0 && (
                <> ({callsPerWeek} calls and {meetingsPerWeek} meetings per week over {goalWeeks} weeks)</>
              )}.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Progress context card */}
      {!pacingDisabled && (callsMade > 0 || meetingsHeld > 0) && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              You&apos;ve made {callsMade} of {callsNeeded} calls and completed{" "}
              {meetingsHeld} of {meetingsNeeded} meetings so far.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
