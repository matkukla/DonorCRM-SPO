import { X } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface FilterBadgeProps {
  /** Human-readable filter name (e.g., "Status") */
  label: string
  /** Human-readable value (e.g., "Active") */
  value: string
  /** Called when the user dismisses the badge */
  onRemove: () => void
}

/**
 * Displays a single active filter as a dismissible badge.
 * Uses the existing Badge component with variant="secondary".
 */
export function FilterBadge({ label, value, onRemove }: FilterBadgeProps) {
  return (
    <Badge variant="secondary" className="gap-1 pr-1">
      <span className="font-medium">{label}:</span>
      <span>{value}</span>
      <button
        type="button"
        onClick={onRemove}
        className="ml-0.5 rounded-sm p-0.5 hover:bg-secondary-foreground/20"
        aria-label={`Remove ${label} filter`}
      >
        <X className="h-3 w-3" />
      </button>
    </Badge>
  )
}
