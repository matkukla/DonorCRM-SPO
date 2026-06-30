import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { JournalReport } from "../ReportCharts"
import type { JournalReportData } from "@/types/journals"

// The Report tab's "Monthly Goal Progress" card must compare GIFT-BASED monthly
// support to the journal's MONTHLY goal (issue #170) — both monthly figures —
// not cumulative confirmed pledges over a monthly goal (the old apples-to-oranges
// math that pinned the bar at 100%). We mock the report hook to control the data.
let mockReport: JournalReportData | undefined

vi.mock("@/hooks/useJournals", () => ({
  useJournalReport: () => ({ data: mockReport, isLoading: false }),
}))

// recharts measures the DOM; jsdom has no layout. Stub the chart primitives so
// the component renders without ResizeObserver/SVG sizing noise.
vi.mock("@/components/ui/chart", () => ({
  ChartContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ChartTooltip: () => null,
  ChartTooltipContent: () => null,
}))

function makeReport(effective: number | null): JournalReportData {
  return {
    metrics: {
      total_contacts: 2,
      with_decisions: 1,
      // A large CUMULATIVE confirmed total — must NOT drive the goal bar.
      confirmed_amount: "5000.00",
      pending_amount: "0.00",
    },
    goal_amount: "1000.00",
    monthly_support:
      effective === null
        ? null
        : {
            recurring_monthly: effective,
            one_time_monthly: 0,
            effective_monthly_support: effective,
            active_pledge_count: 1,
          },
    stage_distribution: [],
    decision_status: [],
    alerts: { stalled_contacts: 0, open_next_steps: 0 },
  }
}

beforeEach(() => {
  mockReport = undefined
})

describe("JournalReport — monthly goal progress basis (#170)", () => {
  it("computes progress from monthly support over the monthly goal", () => {
    // $250/mo gift-based support against a $1,000 monthly goal = 25%.
    mockReport = makeReport(250)
    render(<JournalReport journalId="j-1" goalAmount="1000.00" />)

    expect(screen.getByText("25% of monthly goal")).toBeInTheDocument()
    expect(screen.getByText(/\$250 of \$1,000 monthly support/)).toBeInTheDocument()
  })

  it("does not derive progress from cumulative confirmed pledges", () => {
    // confirmed_amount is $5,000 (5x the goal) but monthly support is $0:
    // the bar must read 0%, proving it ignores the cumulative figure.
    mockReport = makeReport(0)
    render(<JournalReport journalId="j-1" goalAmount="1000.00" />)

    expect(screen.getByText("0% of monthly goal")).toBeInTheDocument()
    // The goal card description shows monthly support ($0), NOT the $5,000
    // cumulative confirmed total. (The separate "Confirmed $" metric card still
    // shows $5,000 — that's informational and intentionally unchanged.)
    expect(screen.getByText(/\$0 of \$1,000 monthly support/)).toBeInTheDocument()
  })

  it("caps progress at 100% when support exceeds the goal", () => {
    mockReport = makeReport(1500)
    render(<JournalReport journalId="j-1" goalAmount="1000.00" />)

    expect(screen.getByText("100% of monthly goal")).toBeInTheDocument()
  })

  it("shows 0% and a fallback label when monthly support is withheld (coach)", () => {
    mockReport = makeReport(null)
    render(<JournalReport journalId="j-1" goalAmount="1000.00" />)

    expect(screen.getByText("0% of monthly goal")).toBeInTheDocument()
    expect(screen.getByText(/Monthly support not available/)).toBeInTheDocument()
  })
})
