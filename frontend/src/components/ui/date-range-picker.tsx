import * as React from "react"
import { Calendar as CalendarIcon } from "lucide-react"
import type { DateRange as DateRangeType } from "@/lib/date-presets"
import { datePresets, formatDateRange } from "@/lib/date-presets"
import { Calendar } from "@/components/ui/calendar"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"

interface DateRangePickerProps {
  value: DateRangeType | null
  onChange: (range: DateRangeType | null) => void
  className?: string
}

export function DateRangePicker({
  value,
  onChange,
  className,
}: DateRangePickerProps) {
  const [open, setOpen] = React.useState(false)

  const handlePresetClick = (preset: () => DateRangeType) => {
    onChange(preset())
    setOpen(false)
  }

  const handleAllTimeClick = () => {
    onChange(null)
    setOpen(false)
  }

  const handleCalendarSelect = (range: { from?: Date; to?: Date } | undefined) => {
    if (range?.from && range?.to) {
      onChange({ from: range.from, to: range.to })
      setOpen(false)
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "justify-start text-left font-normal",
            !value && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {formatDateRange(value)}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="end">
        <div className="flex">
          {/* Preset sidebar */}
          <div className="flex flex-col gap-1 border-r p-3">
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-normal"
              onClick={() => handlePresetClick(datePresets.thisMonth)}
            >
              This Month
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-normal"
              onClick={() => handlePresetClick(datePresets.lastMonth)}
            >
              Last Month
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-normal"
              onClick={() => handlePresetClick(datePresets.lastQuarter)}
            >
              Last Quarter
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-normal"
              onClick={() => handlePresetClick(datePresets.ytd)}
            >
              Year to Date
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start font-normal"
              onClick={handleAllTimeClick}
            >
              All Time
            </Button>
          </div>

          {/* Calendar */}
          <div className="p-3">
            <Calendar
              mode="range"
              selected={value ? { from: value.from, to: value.to } : undefined}
              onSelect={handleCalendarSelect}
              numberOfMonths={2}
            />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
