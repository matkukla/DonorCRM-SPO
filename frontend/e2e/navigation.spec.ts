import { test, expect } from "@playwright/test"

test.describe("Sidebar Navigation", () => {
  test("can navigate to all main pages", async ({ page }) => {
    await page.goto("/")

    const sidebar = page.locator("aside")

    // Navigate to Contacts
    await sidebar.getByRole("link", { name: "Contacts" }).click()
    await expect(page).toHaveURL("/contacts")

    // Navigate to Donations
    await sidebar.getByRole("link", { name: "Donations" }).click()
    await expect(page).toHaveURL("/donations")

    // Navigate to Pledges
    await sidebar.getByRole("link", { name: "Pledges" }).click()
    await expect(page).toHaveURL("/pledges")

    // Navigate to Tasks
    await sidebar.getByRole("link", { name: "Tasks" }).click()
    await expect(page).toHaveURL("/tasks")

    // Navigate to Groups
    await sidebar.getByRole("link", { name: "Groups" }).click()
    await expect(page).toHaveURL("/groups")

    // Navigate to Journals
    await sidebar.getByRole("link", { name: "Journals" }).click()
    await expect(page).toHaveURL("/journals")

    // Navigate back to Dashboard
    await sidebar.getByRole("link", { name: "Dashboard" }).click()
    await expect(page).toHaveURL("/")
  })

  test("insights section expands and navigates", async ({ page }) => {
    await page.goto("/")

    const sidebar = page.locator("aside")

    // Click Insights to expand the collapsible
    await sidebar.getByRole("button", { name: /insights/i }).click()

    // Sub-items should appear
    await expect(sidebar.getByRole("link", { name: "Donations by Month/Year" })).toBeVisible()
    await expect(sidebar.getByRole("link", { name: "Monthly Commitments" })).toBeVisible()
    await expect(sidebar.getByRole("link", { name: "Late Donations" })).toBeVisible()
    await expect(sidebar.getByRole("link", { name: "Follow-ups" })).toBeVisible()

    // Navigate to an insight page
    await sidebar.getByRole("link", { name: "Donations by Month/Year" }).click()
    await expect(page).toHaveURL("/insights/donations-by-month-year")
  })

  test("bottom nav items are accessible", async ({ page }) => {
    await page.goto("/")

    const sidebar = page.locator("aside")

    // Import/Export and Settings should be visible
    await expect(sidebar.getByRole("link", { name: "Import/Export" })).toBeVisible()
    await expect(sidebar.getByRole("link", { name: "Settings" })).toBeVisible()

    // Navigate to Settings
    await sidebar.getByRole("link", { name: "Settings" }).click()
    await expect(page).toHaveURL("/settings")
  })
})
