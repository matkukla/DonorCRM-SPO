/**
 * Shared Recharts color palette for admin analytics.
 *
 * Colors come from the shadcn chart CSS variables (`--chart-1` … `--chart-6`)
 * so light/dark themes stay consistent. Use these everywhere instead of
 * hardcoding `hsl(var(--chart-N))` per file.
 */
export const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
] as const

export const CHART_WARNING_COLOR = "hsl(38 92% 50%)"
