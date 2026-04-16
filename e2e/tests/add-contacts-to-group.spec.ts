import { test, expect, type Page } from "@playwright/test"

const BASE_URL = process.env.BASE_URL || "http://localhost:5173"
const EMAIL = process.env.E2E_EMAIL || "john.smith@spo.org"
const PASSWORD = process.env.E2E_PASSWORD || "***REMOVED***"

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByLabel("Email").fill(EMAIL)
  await page.getByLabel("Password").fill(PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  // Wait for redirect to dashboard after successful login
  await page.waitForURL(`${BASE_URL}/`, { timeout: 10_000 })
}

test.describe("Add contacts to group", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test("bulk action bar appears when contacts are selected", async ({ page }) => {
    await page.goto(`${BASE_URL}/contacts`)
    // Wait for the table to load
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole("row").nth(1)).toBeVisible()

    // No bulk bar yet
    await expect(page.getByText(/contacts selected/)).not.toBeVisible()

    // Select the first contact row's checkbox
    const firstRowCheckbox = page.getByRole("row").nth(1).getByRole("checkbox")
    await firstRowCheckbox.check()

    // Bulk action bar should now be visible
    await expect(page.getByText("1 contact selected")).toBeVisible()
    await expect(page.getByRole("button", { name: /Add to Group/i })).toBeVisible()
  })

  test("Add to Group dialog opens and lists groups", async ({ page }) => {
    await page.goto(`${BASE_URL}/contacts`)
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole("row").nth(1)).toBeVisible()

    // Select first contact
    await page.getByRole("row").nth(1).getByRole("checkbox").check()
    await page.getByRole("button", { name: /Add to Group/i }).click()

    // Dialog should be visible
    await expect(page.getByRole("dialog")).toBeVisible()
    await expect(page.getByRole("heading", { name: "Add to Group" })).toBeVisible()

    // Should show at least one group
    await expect(page.getByRole("dialog").locator("button").first()).toBeVisible({ timeout: 5_000 })
  })

  test("selecting a group adds contacts and shows success toast", async ({ page }) => {
    await page.goto(`${BASE_URL}/contacts`)
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole("row").nth(1)).toBeVisible()

    // Select first contact
    await page.getByRole("row").nth(1).getByRole("checkbox").check()
    await page.getByRole("button", { name: /Add to Group/i }).click()

    // Wait for dialog and groups to load
    await expect(page.getByRole("dialog")).toBeVisible()
    const firstGroup = page.getByRole("dialog").locator("button").first()
    await expect(firstGroup).toBeVisible({ timeout: 5_000 })
    const groupName = await firstGroup.locator("span").first().textContent()

    // Click the first group
    await firstGroup.click()

    // Dialog should close
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 5_000 })

    // Success toast should appear
    await expect(page.getByText(/Added.*contact.*to/i)).toBeVisible({ timeout: 5_000 })
    if (groupName) {
      await expect(page.getByText(new RegExp(groupName.trim(), "i"))).toBeVisible()
    }
  })

  test("select all checkbox selects every visible row", async ({ page }) => {
    await page.goto(`${BASE_URL}/contacts`)
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole("row").nth(1)).toBeVisible()

    // Click the header "select all" checkbox
    const headerCheckbox = page.getByRole("columnheader").getByRole("checkbox")
    await headerCheckbox.check()

    // Bulk bar should show count > 1
    const bulkBar = page.getByText(/contacts selected/)
    await expect(bulkBar).toBeVisible()
    const text = await bulkBar.textContent()
    const count = parseInt(text?.match(/\d+/)?.[0] ?? "0")
    expect(count).toBeGreaterThan(0)
  })

  test("clear button deselects all contacts", async ({ page }) => {
    await page.goto(`${BASE_URL}/contacts`)
    await expect(page.getByRole("table")).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole("row").nth(1)).toBeVisible()

    // Select a contact
    await page.getByRole("row").nth(1).getByRole("checkbox").check()
    await expect(page.getByText("1 contact selected")).toBeVisible()

    // Click Clear
    await page.getByRole("button", { name: "Clear" }).click()

    // Bulk bar should disappear
    await expect(page.getByText(/contacts selected/)).not.toBeVisible()
  })
})
