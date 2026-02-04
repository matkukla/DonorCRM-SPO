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

// Import Center types (SPO CSV imports)
export type ImportType = 'funds' | 'entities' | 'transactions' | 'pledges'

export interface LatestImportRun {
  id: string
  status: string
  created_at: string
  created_count: number
  updated_count: number
  error_count: number
}

export interface DependencyCounts {
  funds_count: number
  entities_with_external_id_count: number
}

export interface LatestImportsResponse {
  funds: LatestImportRun | null
  entities: LatestImportRun | null
  transactions: LatestImportRun | null
  pledges: LatestImportRun | null
  dependency_counts: DependencyCounts
}

// SPO CSV import result (different from legacy ImportResult)
export interface SPOImportResult {
  created_count: number
  updated_count: number
  error_count: number
  errors: string[]
  import_run_id: string | null
}

// SPO Import Center Functions

/**
 * Fetch latest import run for each SPO CSV type
 * Used by Import Center to display tile status
 */
export async function getLatestImports(): Promise<LatestImportsResponse> {
  const response = await apiClient.get('/imports/runs/latest/')
  return response.data
}

/**
 * Import funds from SPO CSV file
 */
export async function importFunds(file: File, validateOnly: boolean = false): Promise<SPOImportResult> {
  const formData = new FormData()
  formData.append("file", file)
  const url = validateOnly ? "/imports/funds/?validate_only=true" : "/imports/funds/"
  const response = await apiClient.post(url, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  })
  return response.data
}

/**
 * Import entities from SPO CSV file
 */
export async function importEntities(file: File, validateOnly: boolean = false): Promise<SPOImportResult> {
  const formData = new FormData()
  formData.append("file", file)
  const url = validateOnly ? "/imports/entities/?validate_only=true" : "/imports/entities/"
  const response = await apiClient.post(url, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  })
  return response.data
}

/**
 * Import transactions from SPO CSV file
 */
export async function importTransactions(file: File, validateOnly: boolean = false): Promise<SPOImportResult> {
  const formData = new FormData()
  formData.append("file", file)
  const url = validateOnly ? "/imports/transactions/?validate_only=true" : "/imports/transactions/"
  const response = await apiClient.post(url, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  })
  return response.data
}

/**
 * Import pledges from SPO CSV file
 */
export async function importPledges(file: File, validateOnly: boolean = false): Promise<SPOImportResult> {
  const formData = new FormData()
  formData.append("file", file)
  const url = validateOnly ? "/imports/pledges/?validate_only=true" : "/imports/pledges/"
  const response = await apiClient.post(url, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  })
  return response.data
}

/**
 * Download errors CSV for an import run
 * Triggers browser download of CSV file with failed rows + error_message column
 */
export async function downloadImportErrorsCSV(importRunId: string, importType: ImportType): Promise<void> {
  const response = await apiClient.get(`/imports/runs/${importRunId}/errors/csv/`, {
    responseType: "blob",
  })

  const filename = `${importType}_errors_${importRunId.slice(0, 8)}.csv`
  downloadFile(response.data, filename, "text/csv")
}

// Legacy Import Functions

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
