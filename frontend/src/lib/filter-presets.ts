import { startOfMonth, endOfMonth, subDays, format } from "date-fns"

export interface FilterPreset {
  id: string
  label: string
  description: string
  getParams: () => Record<string, string | boolean | null>
}

const fmt = (d: Date) => format(d, "yyyy-MM-dd")

// ---------------------------------------------------------------------------
// Contact presets
// ---------------------------------------------------------------------------

export const contactPresets: FilterPreset[] = [
  {
    id: "needs-thank-you",
    label: "Needs Thank You",
    description: "Contacts with unthanked donations",
    getParams: () => ({
      needs_thank_you: "true",
      status: null,
      last_gift_after: null,
      last_gift_before: null,
    }),
  },
  {
    id: "this-month",
    label: "This Month",
    description: "Contacts with gifts this month",
    getParams: () => ({
      last_gift_after: fmt(startOfMonth(new Date())),
      last_gift_before: fmt(endOfMonth(new Date())),
      status: null,
      needs_thank_you: null,
    }),
  },
]

// ---------------------------------------------------------------------------
// Donation presets
// ---------------------------------------------------------------------------

export const donationPresets: FilterPreset[] = [
  {
    id: "unthanked",
    label: "Unthanked",
    description: "Donations not yet thanked",
    getParams: () => ({
      thanked: "false",
      donation_type: null,
      date_after: null,
      date_before: null,
    }),
  },
  {
    id: "this-month",
    label: "This Month",
    description: "Donations received this month",
    getParams: () => ({
      date_after: fmt(startOfMonth(new Date())),
      date_before: fmt(endOfMonth(new Date())),
      thanked: null,
      donation_type: null,
    }),
  },
  {
    id: "last-30-days",
    label: "Last 30 Days",
    description: "Donations in the past 30 days",
    getParams: () => ({
      date_after: fmt(subDays(new Date(), 30)),
      date_before: null,
      thanked: null,
      donation_type: null,
    }),
  },
]

// ---------------------------------------------------------------------------
// Pledge presets
// ---------------------------------------------------------------------------

export const pledgePresets: FilterPreset[] = [
  {
    id: "late-pledges",
    label: "Late Pledges",
    description: "Active pledges that are past due",
    getParams: () => ({
      is_late: "true",
      status: "active",
      frequency: null,
      start_date_after: null,
      start_date_before: null,
    }),
  },
  {
    id: "stalled",
    label: "Stalled",
    description: "Active pledges overdue on payments",
    getParams: () => ({
      status: "active",
      is_late: "true",
      frequency: null,
      start_date_after: null,
      start_date_before: null,
    }),
  },
]
