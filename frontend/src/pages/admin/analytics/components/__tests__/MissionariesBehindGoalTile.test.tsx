import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { MissionariesBehindGoalResponse } from "@/api/adminAnalytics"

vi.mock("@/hooks/useAdminAnalytics", () => ({
  useMissionariesBehindGoal: vi.fn(),
}))

import { useMissionariesBehindGoal } from "@/hooks/useAdminAnalytics"

import { MissionariesBehindGoalTile } from "../MissionariesBehindGoalTile"

type QueryResult = {
  data: MissionariesBehindGoalResponse | undefined
  isLoading: boolean
  error: Error | null
}

function mockHook(result: QueryResult) {
  vi.mocked(useMissionariesBehindGoal).mockReturnValue(
    result as ReturnType<typeof useMissionariesBehindGoal>,
  )
}

const DATA_WITH_ROWS: MissionariesBehindGoalResponse = {
  missionaries: [
    {
      user_id: "u1",
      name: "Alice Behind",
      email: "alice@example.com",
      monthly_goal_cents: 500_000,
      this_month_raised_cents: 100_000,
      pace_percentage: 25,
    },
    {
      user_id: "u2",
      name: "Bob Almost",
      email: "bob@example.com",
      monthly_goal_cents: 400_000,
      this_month_raised_cents: 300_000,
      pace_percentage: 90,
    },
  ],
  total_excluded_no_goal: 3,
  total_missionaries: 8,
  as_of_date: "2026-04-22",
}

describe("MissionariesBehindGoalTile", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a skeleton while loading", () => {
    mockHook({ data: undefined, isLoading: true, error: null })
    render(<MissionariesBehindGoalTile />)
    expect(screen.getByTestId("missionaries-behind-tile")).toHaveAttribute("data-state", "loading")
  })

  it("renders an error state when the hook errors", () => {
    mockHook({ data: undefined, isLoading: false, error: new Error("boom") })
    render(<MissionariesBehindGoalTile />)
    expect(screen.getByTestId("missionaries-behind-tile")).toHaveAttribute("data-state", "error")
  })

  it("renders the empty state with a celebratory message", () => {
    mockHook({
      data: { ...DATA_WITH_ROWS, missionaries: [], total_excluded_no_goal: 0 },
      isLoading: false,
      error: null,
    })
    render(<MissionariesBehindGoalTile />)
    expect(screen.getByText(/all missionaries on pace/i)).toBeInTheDocument()
  })

  it("renders rows for each missionary with formatted currency and pace", () => {
    mockHook({ data: DATA_WITH_ROWS, isLoading: false, error: null })
    render(<MissionariesBehindGoalTile />)

    const rows = screen.getAllByTestId("missionaries-behind-row")
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent("Alice Behind")
    expect(rows[0]).toHaveTextContent("$5,000")
    expect(rows[0]).toHaveTextContent("$1,000")
    expect(rows[0]).toHaveTextContent("25%")

    expect(screen.getByText(/3 missionaries excluded \(no goal set\)/i)).toBeInTheDocument()
  })

  it("calls onUserClick when a row is clicked", () => {
    mockHook({ data: DATA_WITH_ROWS, isLoading: false, error: null })
    const onUserClick = vi.fn()
    render(<MissionariesBehindGoalTile onUserClick={onUserClick} />)

    const rows = screen.getAllByTestId("missionaries-behind-row")
    fireEvent.click(rows[0])
    expect(onUserClick).toHaveBeenCalledWith("u1")
  })

  it("omits the excluded footer when total_excluded_no_goal is 0", () => {
    mockHook({
      data: { ...DATA_WITH_ROWS, total_excluded_no_goal: 0 },
      isLoading: false,
      error: null,
    })
    render(<MissionariesBehindGoalTile />)
    expect(screen.queryByText(/excluded \(no goal set\)/i)).not.toBeInTheDocument()
  })
})
