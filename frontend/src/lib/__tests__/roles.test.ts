import { describe, it, expect } from "vitest"
import type { User } from "@/api/auth"
import { isAdmin, canViewOtherUsers } from "../roles"

function makeUser(role: User["role"]): User {
  return {
    id: "u1",
    email: "u@example.com",
    first_name: "U",
    last_name: "Ser",
    role,
    is_active: true,
    monthly_support_goal_cents: 0,
    dashboard_layout: null,
    coach: null,
  }
}

describe("isAdmin", () => {
  it("is true only for admin", () => {
    expect(isAdmin(makeUser("admin"))).toBe(true)
    expect(isAdmin(makeUser("supervisor"))).toBe(false)
    expect(isAdmin(makeUser("missionary"))).toBe(false)
    expect(isAdmin(makeUser("coach"))).toBe(false)
    expect(isAdmin(null)).toBe(false)
    expect(isAdmin(undefined)).toBe(false)
  })
})

describe("canViewOtherUsers", () => {
  it("is true for admin and supervisor, false for missionary/coach", () => {
    expect(canViewOtherUsers(makeUser("admin"))).toBe(true)
    expect(canViewOtherUsers(makeUser("supervisor"))).toBe(true)
    expect(canViewOtherUsers(makeUser("missionary"))).toBe(false)
    expect(canViewOtherUsers(makeUser("coach"))).toBe(false)
    expect(canViewOtherUsers(null)).toBe(false)
    expect(canViewOtherUsers(undefined)).toBe(false)
  })
})
