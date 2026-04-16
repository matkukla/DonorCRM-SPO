import { test, expect } from "@playwright/test"

test.describe("Dashboard", () => {
  test("loads and shows dashboard content", async ({ page }) => {
    await page.goto("/")

    // Dashboard should be visible (loaded via lazy import)
    // The sidebar should show "Dashboard" as active nav item
    const dashboardNav = page.locator("nav").getByRole("link", { name: "Dashboard" })
    await expect(dashboardNav).toBeVisible()

    // Page should not show login form
    await expect(page.getByLabel("Email")).not.toBeVisible()
  })

  test("sidebar shows expected navigation items for missionary", async ({ page }) => {
    await page.goto("/")

    const nav = page.locator("aside")

    // Core nav items visible to missionaries
    await expect(nav.getByRole("link", { name: "Dashboard" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Contacts" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Donations" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Pledges" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Tasks" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Groups" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Journals" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Prayer" })).toBeVisible()
    await expect(nav.getByRole("link", { name: "Settings" })).toBeVisible()

    // Admin-only items should NOT be visible for missionary
    await expect(nav.getByRole("link", { name: "Admin" })).not.toBeVisible()
    await expect(nav.getByRole("link", { name: "Broadcasts" })).not.toBeVisible()
  })
})
