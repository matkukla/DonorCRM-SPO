import { apiClient, setTokens, clearTokens, getRefreshToken } from "./client"

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
 */
export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken()
  try {
    if (refreshToken) {
      await apiClient.post("/auth/logout/", { refresh: refreshToken })
    }
  } catch {
    // Best-effort revocation: fall back to local clearing below.
  } finally {
    clearTokens()
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
