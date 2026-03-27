import { TableRow, TableCell } from "@/components/ui/table"
import { cn } from "@/lib/utils"

interface MergeFieldRowProps {
  label: string
  fieldName: string
  leftValue: string | null
  rightValue: string | null
  selectedSide: "left" | "right"
  onSideChange: (field: string, side: "left" | "right") => void
  disabled?: boolean
}

export function MergeFieldRow({
  label,
  fieldName,
  leftValue,
  rightValue,
  selectedSide,
  onSideChange,
  disabled,
}: MergeFieldRowProps) {
  const leftDisplay = leftValue || "\u2014"
  const rightDisplay = rightValue || "\u2014"
  const valuesIdentical = (leftValue || "") === (rightValue || "")

  if (valuesIdentical) {
    return (
      <TableRow>
        <TableCell className="font-medium text-sm">{label}</TableCell>
        <TableCell colSpan={2} className="text-center text-sm text-muted-foreground">
          {leftDisplay}
        </TableCell>
      </TableRow>
    )
  }

  return (
    <TableRow>
      <TableCell className="font-medium text-sm">{label}</TableCell>
      <TableCell className="p-0">
        <button
          type="button"
          role="radio"
          aria-checked={selectedSide === "left"}
          aria-label={`${label}: ${leftDisplay}`}
          disabled={disabled}
          onClick={() => onSideChange(fieldName, "left")}
          className={cn(
            "flex items-center gap-2 w-full px-4 py-3 text-sm text-left transition-colors min-h-[44px]",
            selectedSide === "left"
              ? "bg-primary/5 dark:bg-primary/10"
              : "hover:bg-muted/50",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <span
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
              selectedSide === "left"
                ? "border-primary"
                : "border-muted-foreground/40"
            )}
          >
            {selectedSide === "left" && (
              <span className="h-2.5 w-2.5 rounded-full bg-primary" />
            )}
          </span>
          <span className={cn(selectedSide === "left" && "font-medium")}>
            {leftDisplay}
          </span>
        </button>
      </TableCell>
      <TableCell className="p-0">
        <button
          type="button"
          role="radio"
          aria-checked={selectedSide === "right"}
          aria-label={`${label}: ${rightDisplay}`}
          disabled={disabled}
          onClick={() => onSideChange(fieldName, "right")}
          className={cn(
            "flex items-center gap-2 w-full px-4 py-3 text-sm text-left transition-colors min-h-[44px]",
            selectedSide === "right"
              ? "bg-primary/5 dark:bg-primary/10"
              : "hover:bg-muted/50",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <span
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
              selectedSide === "right"
                ? "border-primary"
                : "border-muted-foreground/40"
            )}
          >
            {selectedSide === "right" && (
              <span className="h-2.5 w-2.5 rounded-full bg-primary" />
            )}
          </span>
          <span className={cn(selectedSide === "right" && "font-medium")}>
            {rightDisplay}
          </span>
        </button>
      </TableCell>
    </TableRow>
  )
}
