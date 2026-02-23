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
      owner: null,
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
      owner: null,
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
      payment_method: null,
      date_after: null,
      date_before: null,
      amount_min: null,
      amount_max: null,
      fund: null,
      owner: null,
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
      payment_method: null,
      amount_min: null,
      amount_max: null,
      fund: null,
      owner: null,
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
      payment_method: null,
      amount_min: null,
      amount_max: null,
      fund: null,
      owner: null,
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
      search: null,
      amount_min: null,
      amount_max: null,
    }),
  },
  {
    id: "active",
    label: "Active",
    description: "All currently active pledges",
    getParams: () => ({
      status: "active",
      is_late: null,
      frequency: null,
      start_date_after: null,
      start_date_before: null,
      search: null,
      amount_min: null,
      amount_max: null,
    }),
  },
]

// ---------------------------------------------------------------------------
// Gift presets
// ---------------------------------------------------------------------------

export const giftPresets: FilterPreset[] = [
  {
    id: "this-month",
    label: "This Month",
    description: "Gifts received this month",
    getParams: () => ({
      gift_date_after: fmt(startOfMonth(new Date())),
      gift_date_before: fmt(endOfMonth(new Date())),
      min_amount: null,
      max_amount: null,
      fund: null,
      owner: null,
      donor_contact: null,
    }),
  },
  {
    id: "last-30-days",
    label: "Last 30 Days",
    description: "Gifts in the past 30 days",
    getParams: () => ({
      gift_date_after: fmt(subDays(new Date(), 30)),
      gift_date_before: null,
      min_amount: null,
      max_amount: null,
      fund: null,
      owner: null,
      donor_contact: null,
    }),
  },
]

// ---------------------------------------------------------------------------
// Recurring gift presets
// ---------------------------------------------------------------------------

export const recurringGiftPresets: FilterPreset[] = [
  {
    id: "active",
    label: "Active",
    description: "All currently active recurring gifts",
    getParams: () => ({
      status: "active",
      frequency: null,
      fund: null,
      owner: null,
      donor_contact: null,
    }),
  },
]

// ---------------------------------------------------------------------------
// Journal presets
// ---------------------------------------------------------------------------

export const journalPresets: FilterPreset[] = [
  {
    id: "active-journals",
    label: "Active",
    description: "Non-archived journals",
    getParams: () => ({
      is_archived: null,
      deadline_after: null,
      deadline_before: null,
    }),
  },
  {
    id: "archived",
    label: "Archived",
    description: "Show archived journals",
    getParams: () => ({
      is_archived: "true",
      deadline_after: null,
      deadline_before: null,
    }),
  },
  {
    id: "has-deadline",
    label: "Has Deadline",
    description: "Journals with upcoming deadlines",
    getParams: () => ({
      deadline_after: fmt(new Date()),
      deadline_before: null,
      is_archived: null,
    }),
  },
]
