import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { FiscalYearDonationsResponse } from "@/api/adminAnalytics"

vi.mock("@/hooks/useAdminAnalytics", () => ({
  useFiscalYearDonations: vi.fn(),
}))

// ChartContainer (shadcn) nests ResponsiveContainer. Stub it so jsdom renders
// the chart tree at a fixed size without depending on real layout.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts")
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 600, height: 320 }}>{children}</div>
    ),
  }
})

import { useFiscalYearDonations } from "@/hooks/useAdminAnalytics"

import { FiscalYearDonationsTile } from "../FiscalYearDonationsTile"

type QueryResult = {
  data: FiscalYearDonationsResponse | undefined
  isLoading: boolean
  error: Error | null
}

function mockHook(result: QueryResult) {
  vi.mocked(useFiscalYearDonations).mockReturnValue(
    result as ReturnType<typeof useFiscalYearDonations>,
  )
}

function makeResponse(overrides: Partial<FiscalYearDonationsResponse> = {}): FiscalYearDonationsResponse {
  return {
    fy_start: "2025-07-01",
    fy_end: "2026-06-30",
    months: Array.from({ length: 12 }, (_, i) => ({
      month: `2025-${String(7 + i).padStart(2, "0")}-01`,
      short_label: ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"][i],
      current_cents: i < 3 ? 100_000 * (i + 1) : null,
      prior_cents: 50_000 * (i + 1),
      is_future: i >= 3,
    })),
    current_fy_total_cents: 600_000,
    prior_fy_total_cents: 3_900_000,
    ...overrides,
  }
}

describe("FiscalYearDonationsTile", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a skeleton while loading", () => {
    mockHook({ data: undefined, isLoading: true, error: null })
    render(<FiscalYearDonationsTile />)
    expect(screen.getByTestId("fy-donations-tile")).toHaveAttribute("data-state", "loading")
  })

  it("renders the error state when the hook errors", () => {
    mockHook({ data: undefined, isLoading: false, error: new Error("boom") })
    render(<FiscalYearDonationsTile />)
    expect(screen.getByTestId("fy-donations-tile")).toHaveAttribute("data-state", "error")
  })

  it("renders an empty state when both totals are zero", () => {
    mockHook({
      data: makeResponse({ current_fy_total_cents: 0, prior_fy_total_cents: 0 }),
      isLoading: false,
      error: null,
    })
    render(<FiscalYearDonationsTile />)
    expect(screen.getByText(/no donation data yet/i)).toBeInTheDocument()
  })

  it("renders totals with formatted currency when data is present", () => {
    mockHook({ data: makeResponse(), isLoading: false, error: null })
    render(<FiscalYearDonationsTile />)
    expect(screen.getByTestId("fy-donations-tile")).toHaveAttribute("data-state", "ready")
    expect(screen.getByText(/current fy total/i)).toBeInTheDocument()
    expect(screen.getByText(/prior fy total/i)).toBeInTheDocument()
    // $600,000 current total + $39,000 prior total (see makeResponse defaults)
    expect(screen.getByText("$6,000")).toBeInTheDocument()
    expect(screen.getByText("$39,000")).toBeInTheDocument()
    // Empty-state copy must not appear when data is present.
    expect(screen.queryByText(/no donation data yet/i)).not.toBeInTheDocument()
  })
})
