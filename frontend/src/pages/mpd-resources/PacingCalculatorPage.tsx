import { Loader2, ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { useGoalData } from "@/hooks/useGoal"
import { useViewAs } from "@/providers/ViewAsProvider"

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PACING_CONFIG = {
  AVG_GIFT_AMOUNT: 80,
  CALLS_PER_PARTNER: 9,
  CONVOS_PER_PARTNER: 3,
  APPTS_PER_PARTNER: 1.5,
} as const

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
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
        {label}
      </p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// PacingCalculatorPage
// ---------------------------------------------------------------------------

export default function PacingCalculatorPage() {
  const { data: goalData, isLoading } = useGoalData()
  const { isViewingAs } = useViewAs()

  // Pacing computations
  const goalCents = goalData?.monthly_support_goal_cents ?? 0
  const goalDollarsNum = goalCents / 100
  const pacingDisabled = goalCents === 0

  const partnersNeeded = pacingDisabled
    ? null
    : Math.ceil(goalDollarsNum / PACING_CONFIG.AVG_GIFT_AMOUNT)
  const callsNeeded =
    partnersNeeded !== null
      ? Math.round(partnersNeeded * PACING_CONFIG.CALLS_PER_PARTNER)
      : null
  const convosNeeded =
    partnersNeeded !== null
      ? Math.round(partnersNeeded * PACING_CONFIG.CONVOS_PER_PARTNER)
      : null
  const apptsNeeded =
    partnersNeeded !== null
      ? Math.round(partnersNeeded * PACING_CONFIG.APPTS_PER_PARTNER)
      : null
  const apptsPerWeek =
    apptsNeeded !== null && (goalData?.goal_weeks ?? 0) > 0
      ? Math.ceil(apptsNeeded / goalData!.goal_weeks)
      : null

  const fmt = (val: number | null) => (val !== null ? String(val) : "\u2014")

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
            <PacingTile label="Partners Needed" value={fmt(partnersNeeded)} />
            <PacingTile label="Calls Needed" value={fmt(callsNeeded)} />
            <PacingTile label="Appointments Needed" value={fmt(apptsNeeded)} />
            <PacingTile label="Appointments / Week" value={fmt(apptsPerWeek)} />
          </div>
          {pacingDisabled ? (
            <p className="text-xs text-muted-foreground mt-3">
              Set a goal amount on the Goal page to see pacing targets
            </p>
          ) : (
            <p className="text-xs text-muted-foreground mt-3">
              Based on your {formatCurrency(goalDollarsNum)} goal, we estimate
              you need about {fmt(partnersNeeded)} mission partners, which means
              approximately {fmt(callsNeeded)} calls and {fmt(apptsNeeded)}{" "}
              appointments.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Additional context card */}
      {!pacingDisabled && convosNeeded !== null && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Of those {fmt(callsNeeded)} calls, you should aim for roughly{" "}
              {fmt(convosNeeded)} connected conversations that lead to{" "}
              {fmt(apptsNeeded)} appointments
              {apptsPerWeek !== null && (
                <> ({fmt(apptsPerWeek)} per week over {goalData?.goal_weeks} weeks)</>
              )}
              .
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
