import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { PipelineFunnelConversionResponse } from "@/api/adminAnalytics"

vi.mock("@/hooks/useAdminAnalytics", () => ({
  usePipelineFunnelConversion: vi.fn(),
}))

import { usePipelineFunnelConversion } from "@/hooks/useAdminAnalytics"

import { PipelineFunnelConversionTile } from "../PipelineFunnelConversionTile"

type QueryResult = {
  data: PipelineFunnelConversionResponse | undefined
  isLoading: boolean
  error: Error | null
}

function mockHook(result: QueryResult) {
  vi.mocked(usePipelineFunnelConversion).mockReturnValue(
    result as ReturnType<typeof usePipelineFunnelConversion>,
  )
}

const DATA: PipelineFunnelConversionResponse = {
  stages: [
    {
      stage: "contact",
      label: "Contact",
      count_at_or_past: 100,
      conversion_from_prior_percentage: null,
      is_weakest_transition: false,
    },
    {
      stage: "scheduled",
      label: "Scheduled",
      count_at_or_past: 60,
      conversion_from_prior_percentage: 60,
      is_weakest_transition: false,
    },
    {
      stage: "meet",
      label: "Meet",
      count_at_or_past: 5,
      conversion_from_prior_percentage: 8.3,
      is_weakest_transition: true,
    },
  ],
  total_in_pipeline: 100,
  weakest_transition: { from: "scheduled", to: "meet", rate: 8.3 },
}

describe("PipelineFunnelConversionTile", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a skeleton while loading", () => {
    mockHook({ data: undefined, isLoading: true, error: null })
    render(<PipelineFunnelConversionTile />)
    expect(screen.getByTestId("pipeline-funnel-tile")).toHaveAttribute("data-state", "loading")
  })

  it("renders the empty state when no pipeline activity", () => {
    mockHook({
      data: {
        stages: DATA.stages.map((s) => ({ ...s, count_at_or_past: 0, is_weakest_transition: false })),
        total_in_pipeline: 0,
        weakest_transition: null,
      },
      isLoading: false,
      error: null,
    })
    render(<PipelineFunnelConversionTile />)
    expect(screen.getByText(/no pipeline activity/i)).toBeInTheDocument()
  })

  it("renders one row per stage and shows the weakest badge once", () => {
    mockHook({ data: DATA, isLoading: false, error: null })
    render(<PipelineFunnelConversionTile />)

    expect(screen.getAllByTestId("pipeline-stage-row")).toHaveLength(3)
    const weakest = screen.getAllByTestId("pipeline-weakest-badge")
    expect(weakest).toHaveLength(1)
    expect(weakest[0]).toHaveTextContent("8% conversion")
  })

  it("shows a descriptive weakest-transition footer", () => {
    mockHook({ data: DATA, isLoading: false, error: null })
    render(<PipelineFunnelConversionTile />)
    expect(screen.getByText(/scheduled → meet/i)).toBeInTheDocument()
  })

  it("calls onStageClick when a stage is clicked", () => {
    mockHook({ data: DATA, isLoading: false, error: null })
    const onStageClick = vi.fn()
    render(<PipelineFunnelConversionTile onStageClick={onStageClick} />)

    const firstStageButton = screen.getAllByRole("button")[0]
    fireEvent.click(firstStageButton)
    expect(onStageClick).toHaveBeenCalledWith("contact")
  })
})
