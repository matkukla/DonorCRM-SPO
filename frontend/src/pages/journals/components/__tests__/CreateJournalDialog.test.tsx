import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { CreateJournalDialog } from "../CreateJournalDialog"

// Mock the data hook and side-effect deps so we can render the dialog in
// isolation and assert on the labels/help text the user sees.
const createMutateAsync = vi.fn()

vi.mock("@/hooks/useJournals", () => ({
  useCreateJournal: () => ({ mutateAsync: createMutateAsync, isPending: false }),
}))

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
  createMutateAsync.mockResolvedValue({ id: "j-1" })
})

describe("CreateJournalDialog — monthly goal wording", () => {
  it("labels the goal field as a monthly amount", () => {
    render(<CreateJournalDialog open onOpenChange={vi.fn()} />)

    // The journal goal is a monthly figure (ADR 0008): the label must say so.
    expect(screen.getByLabelText(/monthly goal/i)).toBeInTheDocument()
  })

  it("explains the goal is monthly via help text", () => {
    render(<CreateJournalDialog open onOpenChange={vi.fn()} />)

    expect(screen.getByText(/monthly fundraising target/i)).toBeInTheDocument()
  })
})
