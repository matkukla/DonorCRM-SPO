import { describe, it, expect } from "vitest"
import { formatLastContacted, formatLastTouchLine } from "../last-contacted"

describe("formatLastContacted", () => {
  it("returns 'Never' for null/undefined", () => {
    expect(formatLastContacted(null)).toBe("Never")
    expect(formatLastContacted(undefined)).toBe("Never")
  })

  it("returns a relative '... ago' string for a date", () => {
    const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString()
    expect(formatLastContacted(tenDaysAgo)).toMatch(/ago$/)
  })
})

describe("formatLastTouchLine", () => {
  it("returns 'No logged contact yet' when never touched", () => {
    expect(formatLastTouchLine({ at: null, type: null })).toBe("No logged contact yet")
    expect(formatLastTouchLine(null)).toBe("No logged contact yet")
  })

  it("labels a call touch", () => {
    const at = new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString()
    const line = formatLastTouchLine({ at, type: "call" })
    expect(line).toMatch(/^Last touch: Call, /)
    expect(line).toMatch(/ago$/)
  })

  it("labels a meeting touch", () => {
    const at = new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString()
    const line = formatLastTouchLine({ at, type: "meeting" })
    expect(line).toMatch(/^Last touch: Meeting, /)
  })
})
