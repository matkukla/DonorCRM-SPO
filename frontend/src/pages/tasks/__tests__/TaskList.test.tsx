import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import TaskList from "../TaskList"
import type { Task, TaskFilters } from "@/api/tasks"

// Issue #168: the Tasks tab splits incomplete tasks (active section) from a
// separate "Completed Tasks" section. The split is driven by two queries against
// useTasks -- one with `completed: false`, one with `completed: true` ordered by
// most-recently-completed. These tests pin that the right tasks land in the
// right section and that the completed query is shaped correctly (so the section
// can't silently regress to showing stale/wrong data).

function makeTask(overrides: Partial<Task>): Task {
  return {
    id: "t-active",
    owner: "1",
    owner_name: "Sarah",
    contact: null,
    contact_name: null,
    title: "Active task",
    description: "",
    task_type: "other",
    priority: "medium",
    status: "pending",
    due_date: "2026-07-01",
    due_time: null,
    reminder_date: null,
    is_overdue: false,
    completed_at: null,
    completed_by: null,
    auto_generated: false,
    source_event: null,
    broadcast_id: null,
    broadcast_sender_name: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    ...overrides,
  }
}

const activeTask = makeTask({ id: "t-active", title: "Call a donor" })
const completedTask = makeTask({
  id: "t-done",
  title: "Send thank-you note",
  status: "completed",
  completed_at: "2026-06-20T10:00:00Z",
  completed_by: "1",
})
const completedBroadcastTask = makeTask({
  id: "t-broadcast-done",
  title: "Team update read",
  status: "completed",
  completed_at: "2026-06-21T10:00:00Z",
  completed_by: "1",
  broadcast_id: "b-1",
  broadcast_sender_name: "Director",
})

// Record the filters each useTasks call receives so we can assert the two
// sections request the correct data.
const seenFilters: TaskFilters[] = []

vi.mock("@/hooks/useTasks", () => ({
  useTasks: (filters: TaskFilters) => {
    seenFilters.push(filters)
    if (filters.completed === true) {
      return {
        data: { count: 2, next: null, previous: null, results: [completedBroadcastTask, completedTask] },
        isLoading: false,
      }
    }
    return {
      data: { count: 1, next: null, previous: null, results: [activeTask] },
      isLoading: false,
    }
  },
  useCompleteTask: () => ({ mutate: vi.fn() }),
}))

vi.mock("@/providers/AuthProvider", () => ({
  useAuth: () => ({ user: { id: 1, role: "missionary", first_name: "Sarah", last_name: "M" } }),
}))

vi.mock("@/providers/ViewAsProvider", () => ({
  useViewAs: () => ({ isViewingAs: false }),
}))

function renderTasks() {
  return render(
    <MemoryRouter>
      <TaskList />
    </MemoryRouter>
  )
}

beforeEach(() => {
  seenFilters.length = 0
  vi.clearAllMocks()
})

describe("TaskList — Completed Tasks section (#168)", () => {
  it("renders a separate 'Completed Tasks' section", () => {
    renderTasks()
    expect(screen.getByText("Completed Tasks")).toBeInTheDocument()
  })

  it("queries active (completed: false) and completed (completed: true) tasks", () => {
    renderTasks()
    expect(seenFilters.some((f) => f.completed === false)).toBe(true)
    expect(seenFilters.some((f) => f.completed === true)).toBe(true)
  })

  it("orders the completed query by most-recently-completed first", () => {
    renderTasks()
    const completedQuery = seenFilters.find((f) => f.completed === true)
    expect(completedQuery?.ordering).toBe("-completed_at")
  })

  it("places completed tasks in the completed section, not the active table", () => {
    renderTasks()

    const completedTable = screen.getByRole("table", { name: "Completed tasks" })
    expect(within(completedTable).getByText("Send thank-you note")).toBeInTheDocument()

    const activeTable = screen.getByRole("table", { name: "Active tasks" })
    expect(within(activeTable).getByText("Call a donor")).toBeInTheDocument()
    expect(within(activeTable).queryByText("Send thank-you note")).not.toBeInTheDocument()
  })

  it("shows the user's completed broadcast task in the completed section", () => {
    renderTasks()

    const completedTable = screen.getByRole("table", { name: "Completed tasks" })
    expect(within(completedTable).getByText("Team update read")).toBeInTheDocument()
  })
})
