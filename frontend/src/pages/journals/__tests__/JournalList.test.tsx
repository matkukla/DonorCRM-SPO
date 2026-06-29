import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import JournalList from "../JournalList"

// Navigation is the observable behavior under test (issue #155): the whole card
// must open the journal that the removed "View" link used to open.
const navigateMock = vi.fn()

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom"
  )
  return { ...actual, useNavigate: () => navigateMock }
})

// Stub the data/provider layer so the list renders deterministically without a
// real network/query/auth context.
vi.mock("@/hooks/useJournals", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useJournals")>(
    "@/hooks/useJournals"
  )
  return {
    ...actual,
    useJournals: () => ({
      data: {
        results: [
          {
            id: "j-1",
            name: "Spring Campaign",
            description: null,
            created_at: "2026-01-15",
            owner_name: null,
          },
        ],
      },
      isLoading: false,
      error: null,
    }),
    // CreateJournalDialog (rendered by the page) consumes this; stub it so the
    // page mounts without a real query/mutation layer.
    useCreateJournal: () => ({ mutateAsync: vi.fn(), isPending: false }),
  }
})

vi.mock("@/providers/AuthProvider", () => ({
  useAuth: () => ({ user: { id: 1, role: "missionary" } }),
}))

vi.mock("@/providers/ViewAsProvider", () => ({
  useViewAs: () => ({ isViewingAs: false }),
}))

vi.mock("@/hooks/useFilterParams", async () => {
  const actual = await vi.importActual<
    typeof import("@/hooks/useFilterParams")
  >("@/hooks/useFilterParams")
  return {
    ...actual,
    useFilterParams: () => ({
      filters: {},
      setFilters: vi.fn(),
      clearAll: vi.fn(),
      activeFilters: {},
      activeFilterCount: 0,
      toQueryParams: () => ({}),
    }),
  }
})

function renderList() {
  return render(
    <MemoryRouter>
      <JournalList />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("JournalList — whole card is the click target (#155)", () => {
  it("navigates to the journal when the card is clicked", async () => {
    const user = userEvent.setup()
    renderList()

    await user.click(screen.getByRole("link", { name: "Open journal Spring Campaign" }))

    expect(navigateMock).toHaveBeenCalledWith("/journals/j-1")
  })

  it("navigates when the focused card is activated with Enter", async () => {
    const user = userEvent.setup()
    renderList()

    const card = screen.getByRole("link", { name: "Open journal Spring Campaign" })
    card.focus()
    await user.keyboard("{Enter}")

    expect(navigateMock).toHaveBeenCalledWith("/journals/j-1")
  })

  it("navigates when the focused card is activated with Space", async () => {
    const user = userEvent.setup()
    renderList()

    const card = screen.getByRole("link", { name: "Open journal Spring Campaign" })
    card.focus()
    await user.keyboard(" ")

    expect(navigateMock).toHaveBeenCalledWith("/journals/j-1")
  })

  it("no longer renders the redundant 'View' link", () => {
    renderList()

    expect(screen.queryByText("View")).not.toBeInTheDocument()
  })

  it("makes the card keyboard-focusable", () => {
    renderList()

    const card = screen.getByRole("link", { name: "Open journal Spring Campaign" })
    expect(card).toHaveAttribute("tabindex", "0")
  })
})
