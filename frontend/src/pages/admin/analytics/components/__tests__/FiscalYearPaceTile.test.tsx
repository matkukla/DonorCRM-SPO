import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { FiscalYearPaceResponse } from "@/api/adminAnalytics"

vi.mock("@/hooks/useAdminAnalytics", () => ({
  useFiscalYearPace: vi.fn(),
}))

import { useFiscalYearPace } from "@/hooks/useAdminAnalytics"

import { FiscalYearPaceTile } from "../FiscalYearPaceTile"

type QueryResult = {
  data: FiscalYearPaceResponse | undefined
  isLoading: boolean
  error: Error | null
}

function mockHook(result: QueryResult) {
  vi.mocked(useFiscalYearPace).mockReturnValue(result as ReturnType<typeof useFiscalYearPace>)
}

const BASE_DATA: FiscalYearPaceResponse = {
  fy_start: "2025-07-01",
  fy_end: "2026-06-30",
  raised_cents: 500_000_00,
  annual_goal_cents: 1_000_000_00,
  annual_goal_source: "missionary_sum",
  expected_by_today_cents: 400_000_00,
  pace_percentage: 125.0,
  prior_year_raised_cents: 300_000_00,
  yoy_delta_percentage: 66.7,
  last_import_at: "2026-04-21T10:00:00Z",
}

describe("FiscalYearPaceTile", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a skeleton while loading", () => {
    mockHook({ data: undefined, isLoading: true, error: null })
    render(<FiscalYearPaceTile />)
    expect(screen.getByTestId("fy-pace-tile")).toHaveAttribute("data-state", "loading")
  })

  it("renders an error state when the hook errors", () => {
    mockHook({ data: undefined, isLoading: false, error: new Error("boom") })
    render(<FiscalYearPaceTile />)
    expect(screen.getByTestId("fy-pace-tile")).toHaveAttribute("data-state", "error")
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
  })

  it("formats currency and pace for the happy path", () => {
    mockHook({ data: BASE_DATA, isLoading: false, error: null })
    render(<FiscalYearPaceTile />)

    expect(screen.getByTestId("fy-pace-raised")).toHaveTextContent("$500,000")
    // pace is clamped to 150 and rendered as an integer
    expect(screen.getByTestId("fy-pace-badge")).toHaveTextContent("125% of pace")
    // YoY delta formats with a + sign when positive
    expect(screen.getByTestId("fy-pace-yoy")).toHaveTextContent("+66.7% vs. last year")
    expect(screen.getByTestId("fy-pace-import-caption")).toHaveTextContent(/data as of/i)
  })

  it("shows 'No prior year data' chip when yoy_delta_percentage is null", () => {
    mockHook({
      data: { ...BASE_DATA, yoy_delta_percentage: null },
      isLoading: false,
      error: null,
    })
    render(<FiscalYearPaceTile />)
    expect(screen.getByTestId("fy-pace-yoy")).toHaveTextContent(/no prior year data/i)
  })

  it("falls back to 'Updated daily' caption when last_import_at is null", () => {
    mockHook({
      data: { ...BASE_DATA, last_import_at: null },
      isLoading: false,
      error: null,
    })
    render(<FiscalYearPaceTile />)
    expect(screen.getByTestId("fy-pace-import-caption")).toHaveTextContent(/updated daily/i)
  })

  it("clamps the badge pace to 150% when backend returns an out-of-range value", () => {
    mockHook({
      data: { ...BASE_DATA, pace_percentage: 999 },
      isLoading: false,
      error: null,
    })
    render(<FiscalYearPaceTile />)
    expect(screen.getByTestId("fy-pace-badge")).toHaveTextContent("150% of pace")
  })
})
