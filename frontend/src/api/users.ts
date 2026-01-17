/**
 * Users API client (admin only)
 */
import { apiClient } from "./client"

export type UserRole = "admin" | "staff" | "finance" | "read_only"

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  role: UserRole
  monthly_goal: string | null
  email_notifications: boolean
  is_active: boolean
  date_joined: string
  last_login_at: string | null
}

export interface UserCreate {
  email: string
  first_name: string
  last_name: string
  phone?: string
  role: UserRole
  monthly_goal?: string
  password: string
  password_confirm: string
}

export interface UserUpdate {
  first_name?: string
  last_name?: string
  phone?: string
  role?: UserRole
  monthly_goal?: string
  email_notifications?: boolean
  is_active?: boolean
}

// Labels for display
export const userRoleLabels: Record<UserRole, string> = {
  admin: "Administrator",
  staff: "Staff",
  finance: "Finance",
  read_only: "Read Only",
}

// API functions
export async function getUsers(): Promise<User[]> {
  const response = await apiClient.get("/users/")
  return response.data
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
