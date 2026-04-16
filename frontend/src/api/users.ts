/**
 * Users API client (admin only)
 */
import { apiClient } from "./client"

export type UserRole = "admin" | "missionary" | "supervisor" | "coach"

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  role: UserRole
  monthly_support_goal_cents: number
  email_notifications: boolean
  is_active: boolean
  date_joined: string
  last_login_at: string | null
  supervisor_ids: string[]
  coach_ids: string[]
}

export interface UserCreate {
  email: string
  first_name: string
  last_name: string
  phone?: string
  role: UserRole
  monthly_support_goal_cents?: number
  password: string
  password_confirm: string
}

export interface UserUpdate {
  first_name?: string
  last_name?: string
  phone?: string
  role?: UserRole
  monthly_support_goal_cents?: number
  email_notifications?: boolean
  is_active?: boolean
  supervised_user_ids?: string[]
  coached_user_ids?: string[]
}

// Labels for display
export const userRoleLabels: Record<UserRole, string> = {
  admin: "Administrator",
  supervisor: "Supervisor",
  missionary: "Missionary",
  coach: "Coach",
}

// Numeric levels for role-based access checks (higher = more access)
export const roleHierarchy: Record<UserRole, number> = {
  admin: 4,
  supervisor: 3,
  coach: 2,
  missionary: 1,
}

export interface MissionaryAssignment {
  id: string
  email: string
  full_name: string
  supervisor_ids: string[]
  coach_ids: string[]
}

export interface AssignmentsData {
  missionaries: MissionaryAssignment[]
  supervisors: { id: string; first_name: string; last_name: string; email: string }[]
  coaches: { id: string; first_name: string; last_name: string; email: string }[]
}

export interface AssignmentUpdate {
  missionary_id: string
  supervisor_ids: string[]
  coach_ids: string[]
  additive?: boolean
}

// API functions
export async function getUsers(): Promise<User[]> {
  const response = await apiClient.get("/users/")
  // Backend returns paginated { count, results, ... } — extract the array
  return response.data.results ?? response.data
}

export async function getUser(id: string): Promise<User> {
  const response = await apiClient.get(`/users/${id}/`)
  return response.data
}

export async function createUser(data: UserCreate): Promise<User> {
  const response = await apiClient.post("/users/", data)
  return response.data
}

export async function updateUser(id: string, data: UserUpdate): Promise<User> {
  const response = await apiClient.patch(`/users/${id}/`, data)
  return response.data
}

export async function deactivateUser(id: string): Promise<void> {
  await apiClient.delete(`/users/${id}/`)
}

export async function getAssignments(): Promise<AssignmentsData> {
  const response = await apiClient.get('/users/admin/assignments/')
  return response.data
}

export async function updateAssignments(assignments: AssignmentUpdate[]): Promise<{ updated: number; errors: unknown[] }> {
  const response = await apiClient.patch('/users/admin/assignments/', { assignments })
  return response.data
}

export async function adminResetPassword(
  userId: string,
  data: { new_password: string; new_password_confirm: string }
): Promise<{ detail: string }> {
  const response = await apiClient.post(`/users/${userId}/password/`, data)
  return response.data
}

export interface ViewableUser {
  id: string
  full_name: string
}

export async function getViewableUsers(): Promise<ViewableUser[]> {
  const response = await apiClient.get("/users/viewable/")
  return response.data
}
