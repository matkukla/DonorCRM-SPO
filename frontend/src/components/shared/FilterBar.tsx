import type { ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { FilterBadge } from "@/components/shared/FilterBadge"
import { FilterPresets } from "@/components/shared/FilterPresets"
import { ExportCSVButton } from "@/components/shared/ExportCSVButton"
import type { FilterPreset } from "@/lib/filter-presets"

interface FilterBarProps {
  /** Active filters from useFilterParams (non-null, excluding page/search) */
  activeFilters: [string, string | boolean | number][]
  /** Clear all active filters */
  onClearAll: () => void
  /** Remove a single filter by key */
  onRemoveFilter: (key: string) => void
  /** Maps param keys to human-readable display names */
  filterLabels?: Record<string, string>
  /** Maps param values to human-readable display values per key */
  filterValueLabels?: Record<string, Record<string, string>>
  /** Filter presets to show in the presets dropdown */
  presets?: FilterPreset[]
  /** Called when a preset is selected */
  onApplyPreset?: (preset: FilterPreset) => void
  /** Export endpoint URL (omit to hide export button) */
  exportUrl?: string
  /** Query params to forward to the export endpoint */
  exportParams?: Record<string, string>
  /** Filter control inputs (dropdowns, date pickers, etc.) */
  children: ReactNode
}

/**
 * Reusable filter bar container that composes filter controls,
 * active filter badges, presets dropdown, clear-all button, and CSV export.
 *
 * Layout:
 * ```
 * [children filter controls]                    [Presets] [Export CSV]
 * [badge] [badge] [badge] ... [Clear All]
 * ```
 */
export function FilterBar({
  activeFilters,
  onClearAll,
  onRemoveFilter,
  filterLabels = {},
  filterValueLabels = {},
  presets,
  onApplyPreset,
  exportUrl,
  exportParams,
  children,
}: FilterBarProps) {
  /** Resolve a human-friendly label for a filter key */
  const getLabel = (key: string): string => {
    if (filterLabels[key]) return filterLabels[key]
    // Default: convert snake_case to Title Case
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
  }

  /** Resolve a human-friendly display value */
  const getValue = (key: string, value: string | boolean | number): string => {
    if (typeof value === "boolean") return value ? "Yes" : "No"
    const strVal = String(value)
    if (filterValueLabels[key]?.[strVal]) return filterValueLabels[key][strVal]
    return strVal
  }

  return (
    <div className="space-y-2">
      {/* Top row: filter controls + actions */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {children}
        </div>
        <div className="flex items-center gap-2">
          {presets && onApplyPreset && (
            <FilterPresets presets={presets} onApplyPreset={onApplyPreset} />
          )}
          {exportUrl && exportParams && (
            <ExportCSVButton
              exportUrl={exportUrl}
              queryParams={exportParams}
            />
          )}
        </div>
      </div>

      {/* Bottom row: active filter badges + clear all */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          {activeFilters.map(([key, value]) => (
            <FilterBadge
              key={key}
              label={getLabel(key)}
              value={getValue(key, value)}
              onRemove={() => onRemoveFilter(key)}
            />
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
            className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            Clear All
          </Button>
        </div>
      )}
    </div>
  )
}
