import type { ContactEmailsResponse } from "@/api/contacts"

/**
 * Build the Copy Emails success toast (F8/F9, ADR 0007).
 *
 * Reports what actually landed on the clipboard and what didn't:
 *   "Copied 8 · 1 skipped (no email) · 2 excluded (declined)"
 * Zero-count clauses are omitted.
 */
export function formatCopyEmailsToast(result: ContactEmailsResponse): string {
  const clauses = [`Copied ${result.count}`]
  if (result.skipped_no_email_count > 0) {
    clauses.push(`${result.skipped_no_email_count} skipped (no email)`)
  }
  if (result.declined_excluded_count > 0) {
    clauses.push(`${result.declined_excluded_count} excluded (declined)`)
  }
  return clauses.join(" · ")
}
