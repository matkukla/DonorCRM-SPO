import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createElement } from "react"
import type { ReactNode } from "react"

// Mock the API module so we can assert whether the network call fires.
vi.mock("@/api/users", async () => {
  const actual = await vi.importActual<typeof import("@/api/users")>("@/api/users")
  return {
    ...actual,
    getUsers: vi.fn(),
    getViewableUsers: vi.fn(),
  }
})

import { getUsers, getViewableUsers } from "@/api/users"
import { useUsers, useViewableUsers } from "../useUsers"

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

// A plain missionary must never fire the admin-only `/users/` endpoint or the
// staff-only `/users/viewable/` endpoint — both 403 for that role. Gating the
// hooks with `enabled: false` is how the UI prevents those failing requests.
describe("useUsers gating", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("does NOT call getUsers when disabled (missionary)", () => {
    renderHook(() => useUsers({ enabled: false }), { wrapper: createWrapper() })
    expect(getUsers).not.toHaveBeenCalled()
  })

  it("calls getUsers when enabled (admin)", async () => {
    vi.mocked(getUsers).mockResolvedValue([] as Awaited<ReturnType<typeof getUsers>>)
    renderHook(() => useUsers({ enabled: true }), { wrapper: createWrapper() })
    await waitFor(() => expect(getUsers).toHaveBeenCalled())
  })

  it("calls getUsers by default when no options passed", async () => {
    vi.mocked(getUsers).mockResolvedValue([] as Awaited<ReturnType<typeof getUsers>>)
    renderHook(() => useUsers(), { wrapper: createWrapper() })
    await waitFor(() => expect(getUsers).toHaveBeenCalled())
  })
})

describe("useViewableUsers gating", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("does NOT call getViewableUsers when disabled (missionary)", () => {
    renderHook(() => useViewableUsers({ enabled: false }), { wrapper: createWrapper() })
    expect(getViewableUsers).not.toHaveBeenCalled()
  })

  it("calls getViewableUsers when enabled (admin/supervisor)", async () => {
    vi.mocked(getViewableUsers).mockResolvedValue([] as Awaited<ReturnType<typeof getViewableUsers>>)
    renderHook(() => useViewableUsers({ enabled: true }), { wrapper: createWrapper() })
    await waitFor(() => expect(getViewableUsers).toHaveBeenCalled())
  })
})
