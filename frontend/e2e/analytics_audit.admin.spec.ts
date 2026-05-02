/**
 * Admin-only E2E coverage for the business-analytics audit:
 * - Org Annual Goal card on Settings page
 * - StalledContacts URL pagination persistence
 * - Single-user performance endpoint via UserDetail page
 * - Async-import 400 when CELERY_ENABLED=False
 * - FY Pace tile renders
 *
 * Tests run sequentially within this file so the OrgSettings DB row isn't
 * clobbered by parallel writes.
 */
import { test, expect, type Page } from "@playwright/test"

test.describe.configure({ mode: "serial" })

/**
 * Make an authenticated API call from inside the page context so the JWT in
 * localStorage is automatically attached. Playwright's `page.request` uses a
 * separate context that does NOT carry localStorage.
 */
async function api(
  page: Page,
  init: { method?: string; path: string; body?: unknown },
): Promise<{ status: number; body: string }> {
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

async function ensureLanded(page: Page) {
  await page.goto("/")
  // Wait for any nav element so localStorage is populated and SPA is mounted.
  await expect(page.locator("nav").first()).toBeVisible({ timeout: 10_000 })
}

test.describe("Settings — Organization Annual Goal card (admin)", () => {
  test("admin sees the Organization Annual Goal card", async ({ page }) => {
    await page.goto("/settings")
    await expect(page.getByText("Organization Annual Goal")).toBeVisible()
    await expect(page.getByLabel("Annual Goal ($)")).toBeVisible()
  })

  test("admin can save and persist an annual goal", async ({ page }) => {
    await page.goto("/settings")

    const input = page.getByLabel("Annual Goal ($)")
    await input.fill("")
    await input.fill("123456")

    await page.getByRole("button", { name: /Save Annual Goal/i }).click()
    await expect(page.getByText("Saved", { exact: false })).toBeVisible({ timeout: 5_000 })

    // Round-trip through the API directly: PATCH succeeded if GET returns
    // 12345600 cents.
    const r = await api(page, { path: "/insights/admin/org-settings/" })
    expect(r.status).toBe(200)
    const body = JSON.parse(r.body)
    expect(body.annual_goal_cents).toBe(12_345_600)
  })
})

test.describe("FY Pace tile uses the org goal when set", () => {
  test("admin /admin/analytics/dashboard renders the FY Pace tile", async ({ page }) => {
    await page.goto("/admin/analytics/dashboard")
    await expect(page.getByTestId("fy-pace-tile")).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/Failed to load fiscal year pace\./)).not.toBeVisible()
  })
})

test.describe("StalledContacts — pagination synced to URL", () => {
  test("?page=2 round-trips through reload", async ({ page }) => {
    await page.goto("/admin/analytics/stalled?page=2")
    await expect(page).toHaveURL(/[?&]page=2/)
    await page.reload()
    await expect(page).toHaveURL(/[?&]page=2/)
  })
})

test.describe("Single-user admin performance endpoint", () => {
  test("returns the single user row via /admin/user-performance/<id>/", async ({ page }) => {
    await ensureLanded(page)

    const listResp = await api(page, { path: "/insights/admin/user-performance/" })
    expect(listResp.status).toBe(200)
    const list = JSON.parse(listResp.body)
    expect(Array.isArray(list.users)).toBe(true)
    expect(list.users.length).toBeGreaterThan(0)

    const someUserId = list.users[0].id
    const singleResp = await api(page, {
      path: `/insights/admin/user-performance/${someUserId}/`,
    })
    expect(singleResp.status).toBe(200)
    const single = JSON.parse(singleResp.body)
    expect(single.id).toBe(someUserId)
    expect(typeof single.email).toBe("string")
    expect(typeof single.total_contacts).toBe("number")
  })

  test("returns 404 for a non-existent user id", async ({ page }) => {
    await ensureLanded(page)
    const r = await api(page, {
      path: "/insights/admin/user-performance/00000000-0000-0000-0000-000000000000/",
    })
    expect(r.status).toBe(404)
  })
})

test.describe("Async CSV import — 400 when CELERY_ENABLED=False", () => {
  test("?async=true is rejected with a 400 and a clear message", async ({ page }) => {
    await ensureLanded(page)

    // Build a tiny CSV and POST as multipart from inside the page so the
    // Authorization header is attached by the browser via fetch().
    const result = await page.evaluate(async () => {
      const token = localStorage.getItem("donorcrm_access_token")
      const csv =
        "first_name,last_name,email,phone,address,city,state,zip,country\n" +
        "Jane,Doe,jane.doe@example.com,,,,,,US\n"
      const fd = new FormData()
      fd.append("file", new Blob([csv], { type: "text/csv" }), "contacts.csv")
      const res = await fetch(
        "http://localhost:8000/api/v1/imports/contacts/?async=true",
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: fd,
        },
      )
      return { status: res.status, body: await res.text() }
    })

    expect(result.status).toBe(400)
    const body = JSON.parse(result.body)
    expect(body.detail.toLowerCase()).toMatch(/async|split/)
  })
})

test.describe("OrgSettings endpoint — admin gate + persistence", () => {
  test("GET returns the persisted annual_goal_cents", async ({ page }) => {
    await ensureLanded(page)
    const r = await api(page, { path: "/insights/admin/org-settings/" })
    expect(r.status).toBe(200)
    const body = JSON.parse(r.body)
    expect(typeof body.annual_goal_cents).toBe("number")
    expect(body.annual_goal_cents).toBeGreaterThanOrEqual(0)
  })

  test("PATCH persists annual_goal_cents and feeds the FY pace tile", async ({ page }) => {
    await ensureLanded(page)
    const target = 7_000_000 // $70k

    const r = await api(page, {
      method: "PATCH",
      path: "/insights/admin/org-settings/",
      body: { annual_goal_cents: target },
    })
    expect(r.status).toBe(200)
    expect(JSON.parse(r.body).annual_goal_cents).toBe(target)

    const pace = await api(page, { path: "/insights/admin/fiscal-year-pace/" })
    expect(pace.status).toBe(200)
    const paceBody = JSON.parse(pace.body)
    expect(paceBody.annual_goal_cents).toBe(target)
    expect(paceBody.annual_goal_source).toBe("org_setting")
  })
})
