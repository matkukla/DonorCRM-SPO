/**
 * Currency and number formatting helpers.
 *
 * Money moves as integer cents through the API; always format at the
 * UI boundary, never render raw cents to the user.
 */

const USD_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
})

const USD_WHOLE_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
})

/**
 * Format an integer cents value as a USD currency string.
 *
 * @param cents - Amount in integer cents, or null/undefined
 * @param options.whole - If true, drop the `.00` suffix
 * @returns Formatted currency string or em-dash if nullish
 */
export function formatCents(
  cents: number | null | undefined,
  options?: { whole?: boolean },
): string {
  if (cents === null || cents === undefined) return "—"
  const dollars = cents / 100
  return options?.whole
    ? USD_WHOLE_FORMATTER.format(dollars)
    : USD_FORMATTER.format(dollars)
}

/**
 * Clamp a percentage for display. Backend pace % can exceed 100 — the
 * UI caps at 150 by default so the progress-bar visualization stays
 * meaningful without hiding large overruns entirely.
 */
export function clampPercentage(value: number, min = 0, max = 150): number {
  if (Number.isNaN(value) || !Number.isFinite(value)) return min
  return Math.max(min, Math.min(max, value))
}
