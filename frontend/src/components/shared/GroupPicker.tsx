import { useGroups } from "@/hooks/useGroups"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { ChevronDown, Check } from "lucide-react"
import { useState } from "react"

interface GroupPickerProps {
  value: string[]
  onChange: (ids: string[]) => void
}

export function GroupPicker({ value, onChange }: GroupPickerProps) {
  const { data: groups, isLoading } = useGroups()
  const [open, setOpen] = useState(false)

  const toggle = (id: string) => {
    if (value.includes(id)) {
      onChange(value.filter((v) => v !== id))
    } else {
      onChange([...value, id])
    }
  }

  const allGroups = groups ?? []
  const selectedGroups = allGroups.filter((g) => value.includes(g.id))

  return (
    <div className="space-y-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="secondary"
            className="w-full justify-between font-normal"
            disabled={isLoading}
          >
            {selectedGroups.length === 0
              ? "Select groups..."
              : `${selectedGroups.length} group${selectedGroups.length === 1 ? "" : "s"} selected`}
            <ChevronDown className="h-4 w-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-72 p-2" align="start">
          {isLoading ? (
            <p className="text-sm text-muted-foreground px-2 py-4 text-center">Loading groups...</p>
          ) : !allGroups.length ? (
            <p className="text-sm text-muted-foreground px-2 py-4 text-center">No groups yet</p>
          ) : (
            <div className="max-h-60 overflow-y-auto space-y-1">
              {allGroups.map((group) => {
                const selected = value.includes(group.id)
                return (
                  <button
                    key={group.id}
                    type="button"
                    onClick={() => toggle(group.id)}
                    className="flex items-center gap-2 w-full rounded px-2 py-1.5 text-sm hover:bg-muted transition-colors"
                  >
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: group.color }}
                    />
                    <span className="flex-1 text-left truncate">{group.name}</span>
                    {selected && <Check className="h-4 w-4 text-primary flex-shrink-0" />}
                  </button>
                )
              })}
            </div>
          )}
        </PopoverContent>
      </Popover>

      {selectedGroups.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedGroups.map((group) => (
            <Badge
              key={group.id}
              variant="secondary"
              className="gap-1 cursor-pointer"
              onClick={() => toggle(group.id)}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: group.color }}
              />
              {group.name}
              <span className="ml-0.5 opacity-60">×</span>
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
