import { describe, it, expect } from "vitest"
import { formatCopyEmailsToast } from "../copy-emails"

describe("formatCopyEmailsToast", () => {
  it("reports only copied when nothing skipped or excluded", () => {
    expect(
      formatCopyEmailsToast({
        emails: [],
        count: 8,
        skipped_no_email_count: 0,
        declined_excluded_count: 0,
      }),
    ).toBe("Copied 8")
  })

  it("appends skipped (no email) when present", () => {
    expect(
      formatCopyEmailsToast({
        emails: [],
        count: 8,
        skipped_no_email_count: 1,
        declined_excluded_count: 0,
      }),
    ).toBe("Copied 8 · 1 skipped (no email)")
  })

  it("appends excluded (declined) when present", () => {
    expect(
      formatCopyEmailsToast({
        emails: [],
        count: 8,
        skipped_no_email_count: 0,
        declined_excluded_count: 2,
      }),
    ).toBe("Copied 8 · 2 excluded (declined)")
  })

  it("reports all three clauses", () => {
    expect(
      formatCopyEmailsToast({
        emails: [],
        count: 8,
        skipped_no_email_count: 1,
        declined_excluded_count: 2,
      }),
    ).toBe("Copied 8 · 1 skipped (no email) · 2 excluded (declined)")
  })
})
