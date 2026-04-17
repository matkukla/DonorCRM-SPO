import { test, expect } from "@playwright/test"

test.describe("Contacts", () => {
  test("contact list page loads", async ({ page }) => {
    await page.goto("/contacts")

    // Page heading
    await expect(page.getByRole("heading", { name: /contacts/i })).toBeVisible()

    // "Add Contact" button should be visible for missionaries
    await expect(page.getByRole("button", { name: /add contact/i })).toBeVisible()
  })

  test("can navigate to create contact form", async ({ page }) => {
    await page.goto("/contacts")

    await page.getByRole("button", { name: /add contact/i }).click()

    await expect(page).toHaveURL("/contacts/new")
    await expect(page.getByRole("heading", { name: "Add Contact" })).toBeVisible()
  })

  test("create contact form has required fields", async ({ page }) => {
    await page.goto("/contacts/new")

    // Basic Info fields
    await expect(page.getByLabel("First Name *")).toBeVisible()
    await expect(page.getByLabel("Last Name *")).toBeVisible()
    await expect(page.getByLabel("Organization Name")).toBeVisible()

    // Contact Details
    await expect(page.getByLabel("Email")).toBeVisible()
    await expect(page.getByLabel("Phone", { exact: true })).toBeVisible()

    // Address
    await expect(page.getByLabel("Street Address")).toBeVisible()
    await expect(page.getByLabel("City")).toBeVisible()
    await expect(page.getByLabel("State")).toBeVisible()

    // Actions
    await expect(page.getByRole("button", { name: "Create Contact" })).toBeVisible()
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible()
  })

  test("create contact form validates required fields", async ({ page }) => {
    await page.goto("/contacts/new")

    // Submit without filling anything
    await page.getByRole("button", { name: "Create Contact" }).click()

    // Should show validation error
    await expect(
      page.getByText("First name or organization name is required")
    ).toBeVisible()

    // Should stay on the form
    await expect(page).toHaveURL("/contacts/new")
  })

  test("can create a new contact and see detail page", async ({ page }) => {
    const timestamp = Date.now()
    const firstName = `Zztest${timestamp}`
    const lastName = `Zzlast${timestamp}`

    await page.goto("/contacts/new")

    await page.getByLabel("First Name *").fill(firstName)
    await page.getByLabel("Last Name *").fill(lastName)

    await page.getByRole("button", { name: "Create Contact" }).click()

    // Wait for either redirect to detail page OR duplicate dialog
    const detailUrl = /\/contacts\/[a-f0-9-]+/
    const createAnywayButton = page.getByRole("button", { name: "Create Anyway" })

    await Promise.race([
      expect(page).toHaveURL(detailUrl, { timeout: 10_000 }),
      createAnywayButton.waitFor({ state: "visible", timeout: 10_000 }).then(() =>
        createAnywayButton.click()
      ),
    ])

    // After handling duplicate dialog (if shown), wait for redirect
    await expect(page).toHaveURL(detailUrl, { timeout: 10_000 })

    // Detail page should show the contact name
    await expect(page.getByText(firstName)).toBeVisible()
    await expect(page.getByText(lastName)).toBeVisible()
  })

  test("can search contacts", async ({ page }) => {
    await page.goto("/contacts")

    // Search input should be present
    const searchInput = page.getByPlaceholder(/search/i)
    await expect(searchInput).toBeVisible()

    // Type a search term — the list should filter (or show no results)
    await searchInput.fill("E2E-")
    // Wait for debounced search to take effect
    await page.waitForTimeout(500)

    // Page should still be on contacts
    await expect(page).toHaveURL(/\/contacts/)
  })
})
