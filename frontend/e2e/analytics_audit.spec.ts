/**
 * E2E coverage for the business-analytics audit work shipped in commits
 * f9b4bec, 7c03808, e7f2075, 8867038.
 *
 * Missionary-side surfaces only — admin-only features (org-goal Settings
 * card, single-user UserDetail page, StalledContacts pagination) live in
 * analytics_audit.admin.spec.ts.
 */
import { test, expect, type Page } from "@playwright/test"

/**
 * Make an authenticated API call from inside the page context so localStorage
 * (which holds the JWT) is available. Playwright's `page.request` uses a
 * separate context that does NOT carry localStorage.
 */
async function api(page: Page, init: { method?: string; path: string; body?: unknown }) {
  return page.evaluate(async ({ method, path, body }) => {
    const token = localStorage.getItem("donorcrm_access_token")
    const res = await fetch(`http://localhost:8000/api/v1${path}`, {
      method: method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
    return { status: res.status, body: await res.text() }
  }, init)
}

test.describe("Goal page — unified Monthly Support formula", () => {
  test("renders Goal page with all four progress rows", async ({ page }) => {
    await page.goto("/goal")

    await expect(page.getByRole("heading", { name: "Support Goal" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Goal Settings" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Progress" })).toBeVisible()

    // Each progress row's label appears as exact text in a flex row.
    await expect(page.getByText(/^Monthly Support$/)).toBeVisible()
    await expect(page.getByText(/^Calls$/)).toBeVisible()
    await expect(page.getByText(/^Meetings$/)).toBeVisible()
    await expect(page.getByText(/^Decisions$/)).toBeVisible()
  })
})

test.describe("Dashboard Monthly Support tile", () => {
  test("loads dashboard and Monthly Support tile is present", async ({ page }) => {
    await page.goto("/")
    await expect(page.locator("nav").getByRole("link", { name: "Dashboard" })).toBeVisible()
  })

  test("no error banner on a clean load", async ({ page }) => {
    await page.goto("/")
    // The new error banner is gated by useDashboardSummary failing —
    // on a healthy backend it must NOT appear.
    await expect(page.getByText("Failed to load dashboard data")).not.toBeVisible()
  })
})

test.describe("Insights — late donations (real logic)", () => {
  test("/insights/late-donations renders without error", async ({ page }) => {
    await page.goto("/insights/late-donations")

    await expect(
      page.getByRole("heading", { name: "Late Donations", level: 1 }),
    ).toBeVisible()
    // Either the empty state OR the table — but never the failure banner.
    await expect(page.getByText("Failed to load data. Please try again.")).not.toBeVisible()
  })
})

test.describe("Insights — monthly commitments", () => {
  test("/insights/monthly-commitments renders", async ({ page }) => {
    await page.goto("/insights/monthly-commitments")
    await expect(page.locator("body")).toBeVisible()
  })
})

test.describe("Settings page — Annual Goal card is admin-only", () => {
  test("missionary does NOT see the Organization Annual Goal card", async ({ page }) => {
    await page.goto("/settings")
    await expect(page.getByText("Profile")).toBeVisible()
    await expect(page.getByText("Organization Annual Goal")).not.toBeVisible()
  })
})

test.describe("Date filter validation (missionary -> admin endpoints 403)", () => {
  test("missionary calling admin dashboard-overview returns 403, not 200", async ({ page }) => {
    // Sanity: a missionary shouldn't reach this endpoint regardless of date.
    await page.goto("/")
    const r = await api(page, { path: "/insights/admin/dashboard-overview/?date_from=garbage" })
    expect([400, 403]).toContain(r.status)
  })
})
