import { cn } from "@/lib/utils"

interface GoalProgressBarProps {
  value: number // 0-100+ (fill clamped to 100%, label can show >100%)
  colorVariant?: "support" | "default" // "support" = dynamic color; "default" = primary blue
  disabled?: boolean // muted/greyed state for empty-state rendering
  label?: string // optional accessible label for the bar
  className?: string
}

function getSupportBarColor(pct: number): string {
  if (pct >= 100) return "bg-amber-400" // honey gold at goal
  if (pct >= 75) return "bg-green-500" // green approaching goal
  return "bg-destructive" // red below 75%
}

export function GoalProgressBar({
  value,
  colorVariant = "default",
  disabled = false,
  label,
  className,
}: GoalProgressBarProps) {
  const fillPct = Math.min(value, 100)

  let fillColor: string
  if (disabled) {
    fillColor = "bg-muted"
  } else if (colorVariant === "support") {
    fillColor = getSupportBarColor(value)
  } else {
    fillColor = "bg-primary"
  }

  return (
    <div className={cn("relative w-full", disabled && "opacity-40", className)}>
      {/* Track + fill — no overflow-hidden so tick marks are not clipped */}
      <div
        className="relative w-full h-3 bg-secondary rounded-full"
        role="progressbar"
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={cn(
            "absolute left-0 top-0 h-full rounded-full transition-all duration-300",
            fillColor,
          )}
          style={{ width: `${fillPct}%` }}
        />
      </div>
      {/* Tick marks at 25%, 50%, 75%, 100% — absolutely positioned on wrapper, not on fill */}
      <div className="absolute top-0 h-3 w-px bg-background/70 left-[25%]" />
      <div className="absolute top-0 h-3 w-px bg-background/70 left-[50%]" />
      <div className="absolute top-0 h-3 w-px bg-background/70 left-[75%]" />
      <div className="absolute top-0 h-3 w-px bg-background/70 left-[100%] -translate-x-full" />
    </div>
  )
}
