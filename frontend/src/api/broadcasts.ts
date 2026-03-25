/**
 * Broadcasts API client
 */
import { apiClient } from "./client"
import type { TaskPriority, TaskType, Task, PaginatedResponse } from "./tasks"

// Types
export type BroadcastTargetType = "all_missionaries" | "all_supervisors" | "specific_users" | "my_team"

export interface BroadcastTask {
  id: string
  sender: string
  sender_name: string
  title: string
  description: string
  task_type: TaskType
  priority: TaskPriority
  due_date: string
  target_type: BroadcastTargetType
  recipient_count: number
  completed_count: number
  total_count: number
  is_cancelled: boolean
  cancelled_at: string | null
  created_at: string
}

export interface BroadcastTaskDetail extends BroadcastTask {
  recipient_ids: string[]
}

export interface BroadcastCreate {
  title: string
  description?: string
  task_type?: TaskType
  priority?: TaskPriority
  due_date: string
  target_type: BroadcastTargetType
  specific_user_ids?: string[]
}

export interface BroadcastUpdate {
  title?: string
  description?: string
  task_type?: TaskType
  priority?: TaskPriority
  due_date?: string
}

export interface BroadcastFilters {
  page?: number
  page_size?: number
  ordering?: string
}

// Target type labels for display
export const broadcastTargetLabels: Record<BroadcastTargetType, string> = {
  all_missionaries: "All Missionaries",
  all_supervisors: "All Supervisors",
  specific_users: "Specific Users",
  my_team: "My Team",
}

// API functions
export async function getBroadcasts(filters: BroadcastFilters = {}): Promise<PaginatedResponse<BroadcastTask>> {
  const params = new URLSearchParams()
  if (filters.page) params.append("page", String(filters.page))
  if (filters.page_size) params.append("page_size", String(filters.page_size))
  if (filters.ordering) params.append("ordering", filters.ordering)
  const response = await apiClient.get(`/tasks/broadcasts/?${params.toString()}`)
  return response.data
}

export async function createBroadcast(data: BroadcastCreate): Promise<BroadcastTask> {
  const response = await apiClient.post("/tasks/broadcasts/", data)
  return response.data
}

export async function getBroadcast(id: string): Promise<BroadcastTaskDetail> {
  const response = await apiClient.get(`/tasks/broadcasts/${id}/`)
  return response.data
}

export async function updateBroadcast(id: string, data: BroadcastUpdate): Promise<BroadcastTask> {
  const response = await apiClient.patch(`/tasks/broadcasts/${id}/`, data)
  return response.data
}

export async function cancelBroadcast(id: string): Promise<void> {
  await apiClient.post(`/tasks/broadcasts/${id}/cancel/`)
}

export async function getBroadcastCopies(id: string, page: number = 1): Promise<PaginatedResponse<Task>> {
  const response = await apiClient.get(`/tasks/broadcasts/${id}/copies/?page=${page}`)
  return response.data
}
