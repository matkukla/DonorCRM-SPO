/**
 * Import/Export API client
 */
import { apiClient } from "./client"

// Types
export interface ImportResult {
  imported_count: number
  error_count: number
  errors: string[]
}

export interface ImportError {
  row: number
  message: string
}

// Import Functions

/**
 * Import contacts from CSV file
 * @param file - CSV file to import
 * @param validateOnly - If true, only validate without saving
 */
export async function importContacts(file: File, validateOnly: boolean = false): Promise<ImportResult> {
  const formData = new FormData()
  formData.append("file", file)

  const url = validateOnly ? "/imports/contacts/?validate_only=true" : "/imports/contacts/"
  const response = await apiClient.post(url, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

/**
 * Import donations from CSV file
 * @param file - CSV file to import
 * @param validateOnly - If true, only validate without saving
 */
export async function importDonations(file: File, validateOnly: boolean = false): Promise<ImportResult> {
  const formData = new FormData()
  formData.append("file", file)

  const url = validateOnly ? "/imports/donations/?validate_only=true" : "/imports/donations/"
  const response = await apiClient.post(url, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

// Export Functions

/**
 * Export contacts to CSV - triggers file download
 */
export async function exportContacts(): Promise<void> {
  const response = await apiClient.get("/imports/export/contacts/", {
    responseType: "blob",
  })

  downloadFile(response.data, "contacts_export.csv", "text/csv")
}

/**
 * Export donations to CSV - triggers file download
 * @param startDate - Optional start date filter (YYYY-MM-DD)
 * @param endDate - Optional end date filter (YYYY-MM-DD)
 */
export async function exportDonations(startDate?: string, endDate?: string): Promise<void> {
  const params = new URLSearchParams()
  if (startDate) params.append("start_date", startDate)
  if (endDate) params.append("end_date", endDate)

  const url = `/imports/export/donations/${params.toString() ? "?" + params.toString() : ""}`
  const response = await apiClient.get(url, {
    responseType: "blob",
  })

  const filename = startDate || endDate
    ? `donations_export_${startDate || "all"}_to_${endDate || "all"}.csv`
    : "donations_export.csv"
  downloadFile(response.data, filename, "text/csv")
}

// Template Downloads

/**
 * Download contact import template
 */
export async function downloadContactTemplate(): Promise<void> {
  const response = await apiClient.get("/imports/templates/contacts/", {
    responseType: "blob",
  })
  downloadFile(response.data, "contact_import_template.csv", "text/csv")
}

/**
 * Download donation import template
 */
export async function downloadDonationTemplate(): Promise<void> {
  const response = await apiClient.get("/imports/templates/donations/", {
    responseType: "blob",
  })
  downloadFile(response.data, "donation_import_template.csv", "text/csv")
}

// Helper function to trigger file download
function downloadFile(blob: Blob, filename: string, mimeType: string): void {
  const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }))
  const link = document.createElement("a")
  link.href = url
  link.setAttribute("download", filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
