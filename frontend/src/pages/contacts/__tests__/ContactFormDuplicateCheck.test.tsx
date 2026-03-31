import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { DuplicateWarningDialog } from "../components/DuplicateWarningDialog"
import type { DuplicateMatch } from "@/api/contacts"

const mockMatches: DuplicateMatch[] = [
  {
    id: "dup-1",
    first_name: "John",
    last_name: "Doe",
    full_name: "John Doe",
    email: "john@example.com",
    phone: "555-1234",
    organization_name: "",
    status: "donor",
    confidence: "high",
    reasons: ["Exact email match"],
    similarity: 1.0,
  },
  {
    id: "dup-2",
    first_name: "Jon",
    last_name: "Doe",
    full_name: "Jon Doe",
    email: "",
    phone: "555-5678",
    organization_name: "",
    status: "prospect",
    confidence: "medium",
    reasons: ["Name similarity"],
    similarity: 0.8,
  },
]

describe("DuplicateWarningDialog", () => {
  it("renders dialog title and description when open", () => {
    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    expect(screen.getByText("Possible Duplicates Found")).toBeInTheDocument()
    expect(
      screen.getByText("We found contacts that may be duplicates of the one you're creating.")
    ).toBeInTheDocument()
  })

  it("renders match names, emails, and phones", () => {
    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    expect(screen.getByText("John Doe")).toBeInTheDocument()
    expect(screen.getByText("john@example.com")).toBeInTheDocument()
    expect(screen.getByText("555-1234")).toBeInTheDocument()
    expect(screen.getByText("Jon Doe")).toBeInTheDocument()
    expect(screen.getByText("555-5678")).toBeInTheDocument()
  })

  it("renders confidence badges for each match", () => {
    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    expect(screen.getByText("High")).toBeInTheDocument()
    expect(screen.getByText("Medium")).toBeInTheDocument()
  })

  it("renders View Contact links opening in new tab", () => {
    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    const viewLinks = screen.getAllByText("View Contact")
    expect(viewLinks).toHaveLength(2)
    viewLinks.forEach((link) => {
      expect(link).toHaveAttribute("target", "_blank")
      expect(link).toHaveAttribute("rel", "noopener noreferrer")
    })
  })

  it("calls onKeepEditing when Keep Editing is clicked", async () => {
    const user = userEvent.setup()
    const onKeepEditing = vi.fn()

    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={onKeepEditing}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    await user.click(screen.getByText("Keep Editing"))
    expect(onKeepEditing).toHaveBeenCalledOnce()
  })

  it("calls onCreateAnyway when Create Anyway is clicked", async () => {
    const user = userEvent.setup()
    const onCreateAnyway = vi.fn()

    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={onCreateAnyway}
        isCreating={false}
      />
    )

    await user.click(screen.getByText("Create Anyway"))
    expect(onCreateAnyway).toHaveBeenCalledOnce()
  })

  it("shows max 3 matches even if more are provided", () => {
    const fiveMatches: DuplicateMatch[] = [
      ...mockMatches,
      { ...mockMatches[0], id: "dup-3", full_name: "Match 3" },
      { ...mockMatches[0], id: "dup-4", full_name: "Match 4" },
      { ...mockMatches[0], id: "dup-5", full_name: "Match 5" },
    ]

    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={fiveMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    const viewLinks = screen.getAllByText("View Contact")
    expect(viewLinks).toHaveLength(3)
    // 4th and 5th matches should not render
    expect(screen.queryByText("Match 4")).not.toBeInTheDocument()
    expect(screen.queryByText("Match 5")).not.toBeInTheDocument()
  })

  it("disables buttons when isCreating is true and shows Creating... text", () => {
    render(
      <DuplicateWarningDialog
        open={true}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={true}
      />
    )

    expect(screen.getByText("Creating...")).toBeInTheDocument()
    expect(screen.getByText("Keep Editing")).toBeDisabled()
    expect(screen.getByText("Creating...")).toBeDisabled()
  })

  it("does not render dialog content when closed", () => {
    render(
      <DuplicateWarningDialog
        open={false}
        onOpenChange={vi.fn()}
        matches={mockMatches}
        onKeepEditing={vi.fn()}
        onCreateAnyway={vi.fn()}
        isCreating={false}
      />
    )

    expect(screen.queryByText("Possible Duplicates Found")).not.toBeInTheDocument()
  })
})
