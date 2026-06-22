import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock the API client module: token helpers + base URL. apiClient.post must
// stay untouched — using it for logout is the bug we are guarding against.
vi.mock("@/api/client", () => ({
  apiClient: { post: vi.fn(), get: vi.fn() },
  API_BASE_URL: "http://api.test/api/v1",
  getAccessToken: vi.fn(() => "expired-access"),
  getRefreshToken: vi.fn(() => "old-refresh"),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}))

// Mock the bare axios used by logout.
vi.mock("axios", () => {
  const post = vi.fn()
  const isAxiosError = (e: unknown) => Boolean((e as { isAxiosError?: boolean })?.isAxiosError)
  return { default: { post, isAxiosError }, isAxiosError }
})

import axios from "axios"
import { apiClient, setTokens, clearTokens } from "@/api/client"
import { logout } from "../auth"

const post = vi.mocked(axios.post)

describe("logout token revocation (security report #9)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("refreshes once on expired access, then blacklists the ROTATED refresh token", async () => {
    post.mockImplementation((url: string, body?: unknown) => {
      const refresh = (body as { refresh?: string } | undefined)?.refresh
      if (url.endsWith("/auth/logout/") && refresh === "old-refresh") {
        return Promise.reject({ isAxiosError: true, response: { status: 401 } })
      }
      if (url.endsWith("/auth/refresh/")) {
        return Promise.resolve({ data: { access: "new-access", refresh: "new-refresh" } })
      }
      if (url.endsWith("/auth/logout/") && refresh === "new-refresh") {
        return Promise.resolve({ data: { detail: "Successfully logged out." } })
      }
      return Promise.reject(new Error(`unexpected call ${url} ${refresh}`))
    })

    await logout()

    // The rotated tokens were persisted...
    expect(setTokens).toHaveBeenCalledWith("new-access", "new-refresh")
    // ...and the FINAL logout blacklisted the rotated refresh token, not the stale one.
    const logoutCalls = post.mock.calls.filter(([url]) => String(url).endsWith("/auth/logout/"))
    const lastLogoutBody = logoutCalls[logoutCalls.length - 1][1] as { refresh: string }
    expect(lastLogoutBody.refresh).toBe("new-refresh")
    // Local tokens cleared and the interceptor-bearing client was never used.
    expect(clearTokens).toHaveBeenCalled()
    expect(apiClient.post).not.toHaveBeenCalled()
  })

  it("blacklists the current refresh token directly when access is still valid", async () => {
    post.mockResolvedValue({ data: { detail: "Successfully logged out." } })

    await logout()

    expect(post).toHaveBeenCalledTimes(1)
    const [url, body] = post.mock.calls[0]
    expect(String(url)).toContain("/auth/logout/")
    expect((body as { refresh: string }).refresh).toBe("old-refresh")
    expect(clearTokens).toHaveBeenCalled()
    expect(apiClient.post).not.toHaveBeenCalled()
  })
})
