import type { User } from "@/api/auth"

/**
 * Role helpers for gating client-side requests to staff-only endpoints.
 *
 * Plain missionaries (and coaches) must not fire requests to admin/supervisor
 * endpoints like `/users/` or `/users/viewable/`, which return 403 for them.
 * These predicates mirror the backend permission rules so the UI only requests
 * what the user is allowed to fetch.
 */

/** True for admin only — the gate for the admin-only `/users/` list endpoint. */
export function isAdmin(user: User | null | undefined): boolean {
  return user?.role === "admin"
}

/**
 * True for roles allowed to fetch the View-As "viewable users" list:
 * admin and supervisor. Missionary and coach get 403, so they must not fetch.
 */
export function canViewOtherUsers(user: User | null | undefined): boolean {
  return user?.role === "admin" || user?.role === "supervisor"
}
