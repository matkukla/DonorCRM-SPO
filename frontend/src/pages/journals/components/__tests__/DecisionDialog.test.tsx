import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { DecisionDialog } from "../DecisionDialog"
import type { DecisionSummary } from "@/types/journals"

// Mock the data hooks so we can assert on the payload the dialog submits
// (the observable behavior) without a real network/query layer.
const createMutateAsync = vi.fn()
const updateMutateAsync = vi.fn()

vi.mock("@/hooks/useJournals", () => ({
  useCreateDecision: () => ({ mutateAsync: createMutateAsync, isPending: false }),
  useUpdateDecision: () => ({ mutateAsync: updateMutateAsync, isPending: false }),
}))

const baseProps = {
  open: true,
  onOpenChange: vi.fn(),
  journalContactId: "jc-1",
  journalId: "j-1",
  contactName: "Alice Anderson",
}

beforeEach(() => {
  vi.clearAllMocks()
  createMutateAsync.mockResolvedValue({})
  updateMutateAsync.mockResolvedValue({})
})

describe("DecisionDialog — marking a donor pledged", () => {
  it("submits a create request with amount, cadence, and active status", async () => {
    const user = userEvent.setup()
    render(<DecisionDialog {...baseProps} decision={null} />)

    await user.type(screen.getByLabelText("Amount"), "100")
    await user.click(screen.getByRole("button", { name: "Create Decision" }))

    expect(createMutateAsync).toHaveBeenCalledTimes(1)
    expect(createMutateAsync).toHaveBeenCalledWith({
      journal_contact: "jc-1",
      amount: "100",
      cadence: "monthly",
      status: "pending",
    })
  })

  it("does not submit when the amount is empty (amount is required)", async () => {
    const user = userEvent.setup()
    render(<DecisionDialog {...baseProps} decision={null} />)

    // No amount entered.
    await user.click(screen.getByRole("button", { name: "Create Decision" }))

    expect(createMutateAsync).not.toHaveBeenCalled()
  })

  it("does not submit when the amount is zero", async () => {
    const user = userEvent.setup()
    render(<DecisionDialog {...baseProps} decision={null} />)

    await user.type(screen.getByLabelText("Amount"), "0")
    await user.click(screen.getByRole("button", { name: "Create Decision" }))

    expect(createMutateAsync).not.toHaveBeenCalled()
  })
})

describe("DecisionDialog — editing an existing decision", () => {
  const existing: DecisionSummary = {
    id: "dec-1",
    amount: "250.00",
    cadence: "quarterly",
    status: "pending",
    monthly_equivalent: "83.33",
  }

  it("pre-fills the form from the existing decision", () => {
    render(<DecisionDialog {...baseProps} decision={existing} />)

    expect(screen.getByLabelText("Amount")).toHaveValue(250)
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeInTheDocument()
  })

  it("submits a PATCH with the decision id when activating the pledge", async () => {
    const user = userEvent.setup()
    render(<DecisionDialog {...baseProps} decision={existing} />)

    await user.click(screen.getByRole("button", { name: "Save Changes" }))

    expect(updateMutateAsync).toHaveBeenCalledTimes(1)
    expect(updateMutateAsync).toHaveBeenCalledWith({
      id: "dec-1",
      data: { amount: "250.00", cadence: "quarterly", status: "pending" },
    })
    expect(createMutateAsync).not.toHaveBeenCalled()
  })
})
