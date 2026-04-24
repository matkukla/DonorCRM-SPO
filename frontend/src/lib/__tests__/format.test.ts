import { describe, expect, it } from "vitest"

import { clampPercentage, formatCents } from "@/lib/format"

describe("formatCents", () => {
  it("formats integer cents as USD with cents suffix by default", () => {
    expect(formatCents(12345)).toBe("$123.45")
  })

  it("drops fractional part when whole: true", () => {
    expect(formatCents(12300, { whole: true })).toBe("$123")
  })

  it("rounds whole-formatted fractional cents to nearest dollar", () => {
    expect(formatCents(12399, { whole: true })).toBe("$124")
  })

  it("returns em-dash for null/undefined", () => {
    expect(formatCents(null)).toBe("—")
    expect(formatCents(undefined)).toBe("—")
  })

  it("handles zero", () => {
    expect(formatCents(0)).toBe("$0.00")
    expect(formatCents(0, { whole: true })).toBe("$0")
  })
})

describe("clampPercentage", () => {
  it("passes through values in range", () => {
    expect(clampPercentage(50)).toBe(50)
    expect(clampPercentage(149.9)).toBeCloseTo(149.9)
  })

  it("clamps above the max", () => {
    expect(clampPercentage(999)).toBe(150)
    expect(clampPercentage(999, 0, 100)).toBe(100)
  })

  it("clamps below the min", () => {
    expect(clampPercentage(-25)).toBe(0)
  })

  it("returns min for NaN/Infinity", () => {
    expect(clampPercentage(NaN)).toBe(0)
    expect(clampPercentage(Infinity)).toBe(0)
  })
})
