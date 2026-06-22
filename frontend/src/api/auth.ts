import axios from "axios"

import {
  apiClient,
  API_BASE_URL,
  setTokens,
  clearTokens,
  getAccessToken,
  getRefreshToken,
} from "./client"

export interface LoginCredentials {
  email: string
  password: string
}

export interface TokenResponse {
  access: string
  refresh: string
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: "admin" | "missionary" | "supervisor" | "coach"
  is_active: boolean
  monthly_support_goal_cents: number
  dashboard_layout: { tile_order?: string[] } | null
  supervised_users?: Array<{ id: string; first_name: string; last_name: string; email: string }>
  coach: string | null
}

/**
 * Authenticate user and store JWT tokens
 */
export async function login(credentials: LoginCredentials): Promise<User> {
  // Get tokens
  const tokenResponse = await apiClient.post<TokenResponse>("/auth/login/", credentials)
  setTokens(tokenResponse.data.access, tokenResponse.data.refresh)

  // Fetch user profile
  const userResponse = await apiClient.get<User>("/users/me/")
  return userResponse.data
}

/**
 * Log out: blacklist the refresh token server-side, then clear local tokens.
 *
 * Posting the refresh token to /auth/logout/ invalidates it so a token stolen
 * before logout cannot be reused (security report #14). Local tokens are always
 * cleared, even if the backend call fails (offline/expired), so the user is
 * logged out client-side regardless.
 *
 * Logout deliberately uses a BARE axios instance (no apiClient interceptor).
 * With apiClient, an expired access token would trigger the refresh
 * interceptor, which rotates the refresh token, stores a new one, then retries
 * logout with the STALE refresh token from the original request body. The
 * server rejects the stale token while the freshly-rotated one is never
 * blacklisted — leaving a valid refresh token alive after "logout" (security
 * report #9). Here we instead refresh explicitly and blacklist the token we
 * actually hold.
 */
export async function logout(): Promise<void> {
  try {
    await blacklistRefreshToken()
  } catch {
    // Best-effort revocation: fall back to local clearing below.
  } finally {
    clearTokens()
  }
}

/**
 * Blacklist the current refresh token using an interceptor-free axios call.
 * If the access token is expired (401), refresh once and retry logout with the
 * rotated refresh token so the token in storage is the one that gets revoked.
 */
async function blacklistRefreshToken(): Promise<void> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return

  const access = getAccessToken()
  try {
    await axios.post(
      `${API_BASE_URL}/auth/logout/`,
      { refresh: refreshToken },
      access ? { headers: { Authorization: `Bearer ${access}` } } : undefined
    )
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 401) {
      throw error
    }
    // Access token expired: rotate once, persist, then blacklist the NEW token.
    const refreshed = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
      refresh: refreshToken,
    })
    const { access: newAccess, refresh: newRefresh } = refreshed.data
    setTokens(newAccess, newRefresh)
    await axios.post(
      `${API_BASE_URL}/auth/logout/`,
      { refresh: newRefresh },
      { headers: { Authorization: `Bearer ${newAccess}` } }
    )
  }
}

/**
 * Get current authenticated user
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>("/users/me/")
  return response.data
}

/**
 * Check if user has valid tokens stored
 */
export function hasStoredAuth(): boolean {
  return !!localStorage.getItem("donorcrm_access_token")
}
