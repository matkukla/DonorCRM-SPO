import { formatDistanceToNow } from "date-fns"

/**
 * The "Last Contacted" signal (ADR 0005): the most recent logged call or
 * meeting with a contact. The API returns an ISO datetime, or null when the
 * contact has never been reached via a logged call/meeting.
 */

/** Short label for a table cell: "12 days ago" or "Never". */
export function formatLastContacted(value: string | null | undefined): string {
  if (!value) return "Never"
  return `${formatDistanceToNow(new Date(value))} ago`
}

/**
 * "Last touch" line for the contact Overview, e.g.
 * "Last touch: Call, 12 days ago" or "No logged contact yet".
 */
export function formatLastTouchLine(
  touch: { at: string | null; type: "call" | "meeting" | null } | null | undefined,
): string {
  if (!touch || !touch.at) return "No logged contact yet"
  const kind = touch.type === "meeting" ? "Meeting" : "Call"
  return `Last touch: ${kind}, ${formatDistanceToNow(new Date(touch.at))} ago`
}
