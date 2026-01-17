import { apiClient, setTokens, clearTokens } from "./client"

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
  role: "admin" | "staff" | "finance" | "read_only"
  is_active: boolean
}

/**
 * Authenticate user and store JWT tokens
 */
export async function login(credentials: LoginCredentials): Promise<User> {
  // Get tokens
  const tokenResponse = await apiClient.post<TokenResponse>("/auth/token/", credentials)
  setTokens(tokenResponse.data.access, tokenResponse.data.refresh)

  // Fetch user profile
  const userResponse = await apiClient.get<User>("/users/me/")
  return userResponse.data
}

/**
 * Clear tokens and log out
 */
export function logout(): void {
  clearTokens()
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
