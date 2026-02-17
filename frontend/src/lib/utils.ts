import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Parse a date string as local time to avoid UTC timezone shift.
 *
 * Date-only strings like "2026-02-01" are parsed as UTC midnight by `new Date()`,
 * which displays as Jan 31 in US timezones. This helper detects date-only strings
 * (YYYY-MM-DD) and parses them as local midnight instead. Full ISO timestamps
 * (with "T") are parsed normally.
 */
function parseLocalDate(dateStr: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const [year, month, day] = dateStr.split("-").map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(dateStr)
}

type DateFormatStyle = "short" | "long"

/**
 * Format a date string for display, handling date-only strings as local time.
 *
 * @param dateStr - ISO date string ("2026-02-01") or full timestamp ("2026-02-01T12:00:00Z")
 * @param style - "short" → "Feb 1, 2026", "long" → "February 1, 2026"
 * @returns Formatted date string, or em-dash for null/undefined
 */
export function formatLocalDate(
  dateStr: string | null | undefined,
  style: DateFormatStyle = "short",
): string {
  if (!dateStr) return "\u2014"
  const date = parseLocalDate(dateStr)
  return date.toLocaleDateString("en-US", {
    month: style === "long" ? "long" : "short",
    day: "numeric",
    year: "numeric",
  })
}
