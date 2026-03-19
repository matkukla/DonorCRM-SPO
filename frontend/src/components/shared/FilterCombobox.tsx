import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Filter, Check } from "lucide-react"
import { cn } from "@/lib/utils"

export interface FilterComboboxOption {
  value: string
  label: string
}

interface FilterComboboxProps {
  /** Currently selected value, or null for "all" */
  value: string | null
  /** Called when a value is selected. null means "all" was chosen. */
  onSelect: (value: string | null) => void
  /** Available options (excluding the "all" option which is built in) */
  options: FilterComboboxOption[]
  /** Label shown when nothing is selected (e.g. "All Owners") */
  allLabel?: string
  /** Placeholder text for the search input */
  searchPlaceholder?: string
  /** Text shown when no options match the search */
  emptyText?: string
  /** Button variant */
  variant?: "secondary" | "outline" | "ghost"
  /** Button size */
  size?: "sm" | "default"
}

/**
 * A searchable filter combobox using Popover + Command (shadcn Combobox pattern).
 * Replaces DropdownMenu for filter lists that can be long (e.g., owner filter).
 *
 * Features:
 * - Built-in search input for filtering options
 * - Max-height with scroll for long lists
 * - Keyboard navigation
 * - Built-in "All" option that returns null
 * - Check mark on selected item
 */
export function FilterCombobox({
  value,
  onSelect,
  options,
  allLabel = "All",
  searchPlaceholder = "Search...",
  emptyText = "No results found.",
  variant = "secondary",
  size = "sm",
}: FilterComboboxProps) {
  const [open, setOpen] = useState(false)

  const selectedLabel = value
    ? options.find((opt) => opt.value === value)?.label
    : null

  const handleSelect = (selectedValue: string | null) => {
    onSelect(selectedValue)
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant={variant} size={size} className="gap-2">
          <Filter className="h-4 w-4" />
          {selectedLabel || allLabel}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0" align="start">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {/* "All" option */}
              <CommandItem
                value={allLabel}
                onSelect={() => handleSelect(null)}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    value === null ? "opacity-100" : "opacity-0"
                  )}
                />
                {allLabel}
              </CommandItem>
              {/* Individual options */}
              {options.map((opt) => (
                <CommandItem
                  key={opt.value}
                  value={opt.label}
                  onSelect={() => handleSelect(opt.value)}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === opt.value ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {opt.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
