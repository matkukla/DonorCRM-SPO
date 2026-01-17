/**
 * Tasks API client
 */
import { apiClient } from "./client"

// Types
export type TaskPriority = "low" | "medium" | "high" | "urgent"
export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled"
export type TaskType = "call" | "email" | "thank_you" | "meeting" | "follow_up" | "other"

export interface Task {
  id: string
  owner: string
  owner_name: string
  contact: string | null
  contact_name: string | null
  title: string
  description: string
  task_type: TaskType
  priority: TaskPriority
  status: TaskStatus
  due_date: string
  due_time: string | null
  reminder_date: string | null
  is_overdue: boolean
  completed_at: string | null
  completed_by: string | null
  auto_generated: boolean
  source_event: string | null
  created_at: string
  updated_at: string
}

export interface TaskCreate {
  contact?: string
  title: string
  description?: string
  task_type: TaskType
  priority: TaskPriority
  due_date: string
  due_time?: string
  reminder_date?: string
}

export interface TaskUpdate {
  contact?: string | null
  title?: string
  description?: string
  task_type?: TaskType
  priority?: TaskPriority
  status?: TaskStatus
  due_date?: string
  due_time?: string | null
  reminder_date?: string | null
}

export interface TaskFilters {
  page?: number
  page_size?: number
  status?: TaskStatus
  task_type?: TaskType
  priority?: TaskPriority
  contact?: string
  search?: string
  ordering?: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// Labels for display
export const taskPriorityLabels: Record<TaskPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  urgent: "Urgent",
}

export const taskStatusLabels: Record<TaskStatus, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled: "Cancelled",
}

export const taskTypeLabels: Record<TaskType, string> = {
  call: "Phone Call",
  email: "Email",
  thank_you: "Thank You",
  meeting: "Meeting",
  follow_up: "Follow Up",
  other: "Other",
}

// API functions
export async function getTasks(filters: TaskFilters = {}): Promise<PaginatedResponse<Task>> {
  const params = new URLSearchParams()

  if (filters.page) params.append("page", String(filters.page))
  if (filters.page_size) params.append("page_size", String(filters.page_size))
  if (filters.status) params.append("status", filters.status)
  if (filters.task_type) params.append("task_type", filters.task_type)
  if (filters.priority) params.append("priority", filters.priority)
  if (filters.contact) params.append("contact", filters.contact)
  if (filters.search) params.append("search", filters.search)
  if (filters.ordering) params.append("ordering", filters.ordering)

  const response = await apiClient.get(`/tasks/?${params.toString()}`)
  return response.data
}

export async function getTask(id: string): Promise<Task> {
  const response = await apiClient.get(`/tasks/${id}/`)
  return response.data
}

export async function createTask(data: TaskCreate): Promise<Task> {
  const response = await apiClient.post("/tasks/", data)
  return response.data
}

export async function updateTask(id: string, data: TaskUpdate): Promise<Task> {
  const response = await apiClient.patch(`/tasks/${id}/`, data)
  return response.data
}

export async function deleteTask(id: string): Promise<void> {
  await apiClient.delete(`/tasks/${id}/`)
}

export async function completeTask(id: string): Promise<void> {
  await apiClient.post(`/tasks/${id}/complete/`)
}

export async function getOverdueTasks(): Promise<PaginatedResponse<Task>> {
  const response = await apiClient.get("/tasks/overdue/")
  return response.data
}

export async function getUpcomingTasks(days: number = 7): Promise<PaginatedResponse<Task>> {
  const response = await apiClient.get(`/tasks/upcoming/?days=${days}`)
  return response.data
}
