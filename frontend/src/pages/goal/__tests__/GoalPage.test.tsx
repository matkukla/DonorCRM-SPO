import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { GoalData } from "@/api/goals"

vi.mock("@/hooks/useGoal", () => ({
  useGoalData: vi.fn(),
  useUpdateGoal: vi.fn(),
}))

vi.mock("@/hooks/useJournals", () => ({
  useJournals: vi.fn(),
}))

vi.mock("@/providers/AuthProvider", () => ({
  useAuth: vi.fn(),
}))

vi.mock("@/providers/ViewAsProvider", () => ({
  useViewAs: vi.fn(),
}))

import { useGoalData, useUpdateGoal } from "@/hooks/useGoal"
import { useJournals } from "@/hooks/useJournals"
import { useAuth } from "@/providers/AuthProvider"
import { useViewAs } from "@/providers/ViewAsProvider"

import GoalPage from "../GoalPage"

const GOAL_DATA: GoalData = {
  monthly_support_goal_cents: 350_000, // $3,500
  goal_weeks: 52,
  selected_journal_ids: [],
  effective_monthly_support: 1_000,
  recurring_monthly: 800,
  one_time_monthly: 200,
  calls_count: 0,
  meetings_count: 0,
  decisions_current: 0,
  decisions_goal: 0,
  decisions_percentage: 0,
}

function setup() {
  const mutate = vi.fn()

  vi.mocked(useGoalData).mockReturnValue({
    data: GOAL_DATA,
    isLoading: false,
  } as ReturnType<typeof useGoalData>)

  vi.mocked(useUpdateGoal).mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof useUpdateGoal>)

  vi.mocked(useJournals).mockReturnValue({
    data: { results: [] },
  } as unknown as ReturnType<typeof useJournals>)

  vi.mocked(useAuth).mockReturnValue({
    user: { id: "u1" },
  } as ReturnType<typeof useAuth>)

  vi.mocked(useViewAs).mockReturnValue({
    isViewingAs: false,
  } as ReturnType<typeof useViewAs>)

  render(<GoalPage />)
  return { mutate }
}

describe("GoalPage — save behavior", () => {
  beforeEach(() => vi.clearAllMocks())

  it("saves when pressing Enter in the Monthly Goal field", () => {
    const { mutate } = setup()

    const input = screen.getByLabelText("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "4200" } })
    fireEvent.keyDown(input, { key: "Enter" })

    expect(mutate).toHaveBeenCalledTimes(1)
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        monthly_support_goal_cents: 420_000,
        goal_weeks: 52,
        journal_ids: [],
      }),
      expect.anything(),
    )
  })

  it("produces an identical save to clicking Save Settings", () => {
    const { mutate } = setup()

    const input = screen.getByLabelText("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "4200" } })

    // Click path
    fireEvent.click(screen.getByRole("button", { name: /save settings/i }))
    const clickPayload = mutate.mock.calls[0][0]

    mutate.mockClear()

    // Enter path
    fireEvent.keyDown(input, { key: "Enter" })
    const enterPayload = mutate.mock.calls[0][0]

    expect(enterPayload).toEqual(clickPayload)
  })

  it("does not save on Enter when a non-Enter key is pressed", () => {
    const { mutate } = setup()

    const input = screen.getByLabelText("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "4200" } })
    fireEvent.keyDown(input, { key: "a" })

    expect(mutate).not.toHaveBeenCalled()
  })
})
