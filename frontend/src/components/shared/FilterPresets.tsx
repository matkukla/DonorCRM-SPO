import { ListFilter } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { FilterPreset } from "@/lib/filter-presets"

interface FilterPresetsProps {
  presets: FilterPreset[]
  onApplyPreset: (preset: FilterPreset) => void
}

/**
 * Dropdown button to select and apply a filter preset.
 * Each item shows the preset label and description.
 */
export function FilterPresets({ presets, onApplyPreset }: FilterPresetsProps) {
  if (presets.length === 0) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" size="sm">
          <ListFilter className="mr-1 h-4 w-4" />
          Presets
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {presets.map((preset) => (
          <DropdownMenuItem
            key={preset.id}
            onClick={() => onApplyPreset(preset)}
            className="flex flex-col items-start gap-0.5"
          >
            <span className="font-medium">{preset.label}</span>
            <span className="text-xs text-muted-foreground">
              {preset.description}
            </span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
