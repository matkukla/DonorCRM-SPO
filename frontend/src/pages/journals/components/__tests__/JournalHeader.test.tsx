import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { JournalHeader } from "../JournalHeader"
import type { JournalDetail, JournalReportData } from "@/types/journals"

// The header's goal-progress bar must reflect GIFT-BASED monthly support
// (issue #167), not cumulative pledges. We mock the report hook to control
// effective_monthly_support and the journal's monthly goal.
let mockReport: JournalReportData | undefined

vi.mock("@/hooks/useJournals", () => ({
  useJournalReport: () => ({ data: mockReport }),
  useUpdateJournal: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/providers/ViewAsProvider", () => ({
  useViewAs: () => ({ isViewingAs: false }),
}))

const journal: JournalDetail = {
  id: "j-1",
  name: "MPD 2026",
  goal_amount: "1000.00", // monthly goal
  deadline: null,
  is_archived: false,
  owner: "u-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  contact_count: 1,
} as unknown as JournalDetail

function makeReport(effective: number | null): JournalReportData {
  return {
    metrics: {
      total_contacts: 1,
      with_decisions: 1,
      confirmed_amount: "0.00",
      pending_amount: "0.00",
    },
    goal_amount: "1000.00",
    monthly_support:
      effective === null
        ? null
        : {
            recurring_monthly: 0,
            one_time_monthly: effective,
            effective_monthly_support: effective,
            active_pledge_count: 0,
          },
    stage_distribution: [],
    decision_status: [],
    alerts: { stalled_contacts: 0, open_next_steps: 0 },
  }
}

beforeEach(() => {
  mockReport = undefined
})

describe("JournalHeader — gift-based goal progress (#167)", () => {
  it("shows progress as effective monthly support over the monthly goal", () => {
    // $100/mo gift-based support against a $1000 monthly goal = 10%.
    mockReport = makeReport(100)
    render(<JournalHeader journal={journal} members={[]} />)

    expect(screen.getByText(/10% of goal/)).toBeInTheDocument()
    expect(screen.getByText(/\$100 \/ \$1,000 monthly support/)).toBeInTheDocument()
  })

  it("does not derive progress from pledged decision amounts", () => {
    // A large pledge must NOT move the goal bar — only gifts do.
    mockReport = makeReport(0)
    const members = [
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      { decision: { amount: "5000.00", status: "active" } } as any,
    ]
    render(<JournalHeader journal={journal} members={members} />)

    // Pledged text still shows, but the goal bar is 0% (no gifts received).
    expect(screen.getByText(/0% of goal/)).toBeInTheDocument()
    expect(screen.getByText(/\$5,000 pledged/)).toBeInTheDocument()
  })

  it("falls back gracefully when monthly support is withheld (coach)", () => {
    mockReport = makeReport(null)
    render(<JournalHeader journal={journal} members={[]} />)

    expect(screen.getByText(/0% of goal/)).toBeInTheDocument()
  })
})
