/**
 * MPD (Smartsheet) Import API client
 */
import { apiClient } from "./client"

// Types

/** Upload response from POST /api/v1/imports/mpd/ */
export interface MPDUploadResult {
  upload_id: string
  status: "completed" | "failed"
  total_rows: number
  matched_count: number
  unmatched_count: number
  unmatched_rows: MPDUnmatchedRow[]
  snapshot_count: number
  error?: string
}

export interface MPDUnmatchedRow {
  row: number
  first_name: string
  last_name: string
  current_mpd_cap: string | null
  latest_roll_forward_balance: string | null
  months_remaining_rf: string
}

/** Overview response from GET /api/v1/imports/mpd/overview/ */
export interface MPDOverviewResponse {
  missionaries: MPDMissionaryOverview[]
}

export interface MPDMissionaryOverview {
  user_id: string
  user_name: string
  current_mpd_cap: string | null
  latest_roll_forward_balance: string | null
  months_remaining_rf: string
}

/** My data response from GET /api/v1/imports/mpd/me/ */
export interface MPDMyDataResponse {
  has_data: boolean
  current_mpd_cap?: string | null
  latest_roll_forward_balance?: string | null
  months_remaining_rf?: string
}

/** Upload history response from GET /api/v1/imports/mpd/uploads/ */
export interface MPDUploadHistoryItem {
  id: string
  filename: string
  created_at: string
  total_rows: number
  matched_count: number
  unmatched_count: number
}

// API Functions

/**
 * Upload an MPD Smartsheet file (CSV or XLSX)
 * Backend auto-detects format from file content
 */
export async function uploadMPDFile(file: File): Promise<MPDUploadResult> {
  const formData = new FormData()
  formData.append("file", file)
  const response = await apiClient.post("/imports/mpd/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return response.data
}

/**
 * Fetch per-missionary latest MPD data (admin only)
 */
export async function getMPDOverview(): Promise<MPDOverviewResponse> {
  const response = await apiClient.get("/imports/mpd/overview/")
  return response.data
}

/**
 * Fetch current user's own MPD snapshot
 */
export async function getMPDMyData(): Promise<MPDMyDataResponse> {
  const response = await apiClient.get("/imports/mpd/me/")
  return response.data
}

/**
 * Fetch MPD upload history (admin only)
 */
export async function getMPDUploadHistory(): Promise<MPDUploadHistoryItem[]> {
  const response = await apiClient.get("/imports/mpd/uploads/")
  return response.data.uploads
}

// Helpers

/**
 * Format a decimal string value as USD currency
 * Handles the DecimalField-as-string pitfall (values come as "71352.72" strings)
 */
export function formatMPDCurrency(value: string | null): string {
  if (!value) return "--"
  const num = parseFloat(value)
  if (isNaN(num)) return "--"
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}
