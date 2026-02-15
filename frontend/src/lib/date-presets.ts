import {
  startOfMonth,
  endOfMonth,
  subMonths,
  startOfQuarter,
  endOfQuarter,
  subQuarters,
  startOfYear,
  format,
} from "date-fns"

export interface DateRange {
  from: Date
  to: Date
}

export const datePresets = {
  thisMonth: (): DateRange => {
    const now = new Date()
    return {
      from: startOfMonth(now),
      to: endOfMonth(now),
    }
  },
  lastMonth: (): DateRange => {
    const now = new Date()
    const lastMonth = subMonths(now, 1)
    return {
      from: startOfMonth(lastMonth),
      to: endOfMonth(lastMonth),
    }
  },
  lastQuarter: (): DateRange => {
    const now = new Date()
    const lastQuarter = subQuarters(now, 1)
    return {
      from: startOfQuarter(lastQuarter),
      to: endOfQuarter(lastQuarter),
    }
  },
  ytd: (): DateRange => {
    const now = new Date()
    return {
      from: startOfYear(now),
      to: now,
    }
  },
}

export function formatDateRange(range: DateRange | null): string {
  if (!range) {
    return "All time"
  }
  const fromStr = format(range.from, "MMM d, yyyy")
  const toStr = format(range.to, "MMM d, yyyy")
  return `${fromStr} - ${toStr}`
}

export function dateRangeToParams(range: DateRange | null): {
  date_from?: string
  date_to?: string
} {
  if (!range) {
    return {}
  }
  return {
    date_from: format(range.from, "yyyy-MM-dd"),
    date_to: format(range.to, "yyyy-MM-dd"),
  }
}
