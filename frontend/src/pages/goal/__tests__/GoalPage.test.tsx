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

interface TestJournal {
  id: string
  name: string
  goal_amount: string
}

interface SetupOptions {
  goalData?: Partial<GoalData>
  journals?: TestJournal[]
}

function setup(options: SetupOptions = {}) {
  const mutate = vi.fn()
  const goalData = { ...GOAL_DATA, ...options.goalData }
  const journals = options.journals ?? []

  vi.mocked(useGoalData).mockReturnValue({
    data: goalData,
    isLoading: false,
  } as ReturnType<typeof useGoalData>)

  vi.mocked(useUpdateGoal).mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof useUpdateGoal>)

  vi.mocked(useJournals).mockReturnValue({
    data: { results: journals },
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

describe("GoalPage — auto-populate Monthly Goal from selected journals", () => {
  beforeEach(() => vi.clearAllMocks())

  it("overwrites the Monthly Goal with the sum of checked journals on Save", () => {
    const { mutate } = setup({
      journals: [
        { id: "j1", name: "Alpha", goal_amount: "500.00" },
        { id: "j2", name: "Beta", goal_amount: "250.00" },
      ],
    })

    // User typed a manual value that should be overwritten by the sum.
    const input = screen.getByLabelText("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "9999" } })

    // Check both journals, then save.
    fireEvent.click(screen.getByLabelText("Alpha"))
    fireEvent.click(screen.getByLabelText("Beta"))
    fireEvent.click(screen.getByRole("button", { name: /save settings/i }))

    expect(mutate).toHaveBeenCalledTimes(1)
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        monthly_support_goal_cents: 75_000, // $500 + $250 = $750
        journal_ids: ["j1", "j2"],
      }),
      expect.anything(),
    )
  })

  it("keeps the manually typed value when no journals are checked", () => {
    const { mutate } = setup({
      journals: [
        { id: "j1", name: "Alpha", goal_amount: "500.00" },
        { id: "j2", name: "Beta", goal_amount: "250.00" },
      ],
    })

    // Journals exist but the user checks none — the typed value must survive.
    const input = screen.getByLabelText("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "4200" } })
    fireEvent.click(screen.getByRole("button", { name: /save settings/i }))

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        monthly_support_goal_cents: 420_000,
        journal_ids: [],
      }),
      expect.anything(),
    )
  })

  it("reflects the summed total back into the Monthly Goal input", () => {
    setup({
      journals: [
        { id: "j1", name: "Alpha", goal_amount: "500.00" },
        { id: "j2", name: "Beta", goal_amount: "250.00" },
      ],
    })

    const input = screen.getByLabelText<HTMLInputElement>("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "9999" } })
    fireEvent.click(screen.getByLabelText("Alpha"))
    fireEvent.click(screen.getByLabelText("Beta"))
    fireEvent.click(screen.getByRole("button", { name: /save settings/i }))

    expect(input.value).toBe("750")
  })

  it("sums to exact cents for fractional dollar amounts", () => {
    const { mutate } = setup({
      journals: [
        { id: "j1", name: "Alpha", goal_amount: "333.33" },
        { id: "j2", name: "Beta", goal_amount: "333.33" },
        { id: "j3", name: "Gamma", goal_amount: "333.34" },
      ],
    })

    fireEvent.click(screen.getByLabelText("Alpha"))
    fireEvent.click(screen.getByLabelText("Beta"))
    fireEvent.click(screen.getByLabelText("Gamma"))
    fireEvent.click(screen.getByRole("button", { name: /save settings/i }))

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        // 33333 + 33333 + 33334 = 100000 cents ($1,000.00), exact.
        monthly_support_goal_cents: 100_000,
      }),
      expect.anything(),
    )
  })

  it("sums the checked journals when saving via Enter", () => {
    const { mutate } = setup({
      journals: [
        { id: "j1", name: "Alpha", goal_amount: "500.00" },
        { id: "j2", name: "Beta", goal_amount: "250.00" },
      ],
    })

    const input = screen.getByLabelText("Monthly Goal ($)")
    fireEvent.change(input, { target: { value: "9999" } })
    fireEvent.click(screen.getByLabelText("Alpha"))
    fireEvent.click(screen.getByLabelText("Beta"))
    fireEvent.keyDown(input, { key: "Enter" })

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        monthly_support_goal_cents: 75_000,
        journal_ids: ["j1", "j2"],
      }),
      expect.anything(),
    )
  })
})
