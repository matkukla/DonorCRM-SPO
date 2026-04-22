import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { WeeklyEngagementResponse } from "@/api/adminAnalytics"

vi.mock("@/hooks/useAdminAnalytics", () => ({
  useWeeklyEngagement: vi.fn(),
}))

// ChartContainer (shadcn wrapper around Recharts) nests ResponsiveContainer
// internally. ResponsiveContainer needs real layout which jsdom can't provide,
// so stub it with a fixed-size div that still renders its children.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts")
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 600, height: 300 }}>{children}</div>
    ),
  }
})

import { useWeeklyEngagement } from "@/hooks/useAdminAnalytics"

import { WeeklyEngagementTile } from "../WeeklyEngagementTile"

type QueryResult = {
  data: WeeklyEngagementResponse | undefined
  isLoading: boolean
  error: Error | null
}

function mockHook(result: QueryResult) {
  vi.mocked(useWeeklyEngagement).mockReturnValue(
    result as ReturnType<typeof useWeeklyEngagement>,
  )
}

function makeWeeks(n: number, active: number, onPace: number): WeeklyEngagementResponse {
  return {
    weeks: Array.from({ length: n }, (_, i) => ({
      week_start: `2026-02-${String((i % 28) + 1).padStart(2, "0")}`,
      week_label: `Feb ${i + 1}`,
      active_missionaries: active,
      on_pace_missionaries: onPace,
      total_missionaries: 40,
    })),
  }
}

describe("WeeklyEngagementTile", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a skeleton while loading", () => {
    mockHook({ data: undefined, isLoading: true, error: null })
    render(<WeeklyEngagementTile />)
    expect(screen.getByTestId("weekly-engagement-tile")).toHaveAttribute("data-state", "loading")
  })

  it("renders an error state when the hook errors", () => {
    mockHook({ data: undefined, isLoading: false, error: new Error("boom") })
    render(<WeeklyEngagementTile />)
    expect(screen.getByTestId("weekly-engagement-tile")).toHaveAttribute("data-state", "error")
  })

  it("renders the empty state when all weeks are zero", () => {
    mockHook({ data: makeWeeks(4, 0, 0), isLoading: false, error: null })
    render(<WeeklyEngagementTile />)
    expect(screen.getByText(/no engagement data/i)).toBeInTheDocument()
  })

  it("reaches the ready state with a descriptive caption when data is present", () => {
    mockHook({ data: makeWeeks(12, 8, 4), isLoading: false, error: null })
    render(<WeeklyEngagementTile />)
    expect(screen.getByTestId("weekly-engagement-tile")).toHaveAttribute("data-state", "ready")
    // Card description varies with the weeks prop and confirms data path executed.
    expect(screen.getByText(/last 12 weeks/i)).toBeInTheDocument()
    // Empty-state copy must not appear when data is present.
    expect(screen.queryByText(/no engagement data/i)).not.toBeInTheDocument()
  })

  it("honors the weeks prop in the description", () => {
    mockHook({ data: makeWeeks(4, 3, 1), isLoading: false, error: null })
    render(<WeeklyEngagementTile weeks={4} />)
    expect(screen.getByText(/last 4 weeks/i)).toBeInTheDocument()
  })
})
