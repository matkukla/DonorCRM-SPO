import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createElement } from "react"
import type { ReactNode } from "react"

// Mock the API module
vi.mock("@/api/contacts", async () => {
  const actual = await vi.importActual<typeof import("@/api/contacts")>("@/api/contacts")
  return {
    ...actual,
    checkDuplicates: vi.fn(),
    scanDuplicates: vi.fn(),
    mergeContacts: vi.fn(),
    dismissDuplicate: vi.fn(),
  }
})

import { checkDuplicates, mergeContacts, dismissDuplicate } from "@/api/contacts"
import { useCheckDuplicates, useMergeContacts, useDismissDuplicate } from "../useContacts"

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe("useCheckDuplicates", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("calls checkDuplicates API and returns matches", async () => {
    const mockMatches = [
      { id: "1", full_name: "John Doe", confidence: "high", reasons: ["Exact email match"], similarity: 1.0 },
    ]
    vi.mocked(checkDuplicates).mockResolvedValue(mockMatches as ReturnType<typeof checkDuplicates> extends Promise<infer T> ? T : never)

    const { result } = renderHook(() => useCheckDuplicates(), { wrapper: createWrapper() })

    result.current.mutate({ first_name: "John", last_name: "Doe", email: "john@test.com" })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockMatches)
    expect(checkDuplicates).toHaveBeenCalledWith({ first_name: "John", last_name: "Doe", email: "john@test.com" })
  })

  it("handles API error gracefully", async () => {
    vi.mocked(checkDuplicates).mockRejectedValue(new Error("Network error"))

    const { result } = renderHook(() => useCheckDuplicates(), { wrapper: createWrapper() })

    result.current.mutate({ first_name: "John" })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeTruthy()
  })
})

describe("useMergeContacts", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("calls mergeContacts API with correct payload", async () => {
    const mockResult = { id: "survivor-1", full_name: "John Doe" }
    vi.mocked(mergeContacts).mockResolvedValue(mockResult as ReturnType<typeof mergeContacts> extends Promise<infer T> ? T : never)

    const { result } = renderHook(() => useMergeContacts(), { wrapper: createWrapper() })

    result.current.mutate({ survivor_id: "survivor-1", loser_id: "loser-1", field_overrides: { email: "right" } })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mergeContacts).toHaveBeenCalledWith({
      survivor_id: "survivor-1",
      loser_id: "loser-1",
      field_overrides: { email: "right" },
    })
  })
})

describe("useDismissDuplicate", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("calls dismissDuplicate API with contact pair IDs", async () => {
    vi.mocked(dismissDuplicate).mockResolvedValue(undefined)

    const { result } = renderHook(() => useDismissDuplicate(), { wrapper: createWrapper() })

    result.current.mutate({ contact_a_id: "id-a", contact_b_id: "id-b" })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(dismissDuplicate).toHaveBeenCalledWith({ contact_a_id: "id-a", contact_b_id: "id-b" })
  })
})
