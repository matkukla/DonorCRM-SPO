import { test, expect } from "@playwright/test"

// These tests run WITHOUT stored auth to verify redirect behavior.
test.use({ storageState: { cookies: [], origins: [] } })

test.describe("Auth Guard", () => {
  test("unauthenticated user is redirected to login", async ({ page }) => {
    await page.goto("/contacts")

    // Should redirect to login page
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
  })

  test("unauthenticated user cannot access dashboard", async ({ page }) => {
    await page.goto("/")

    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
  })

  test("unauthenticated user cannot access settings", async ({ page }) => {
    await page.goto("/settings")

    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
  })

  test("login page is accessible without auth", async ({ page }) => {
    await page.goto("/login")

    // Should stay on login page (no redirect)
    await expect(page).toHaveURL("/login")
    await expect(page.getByText("Welcome back")).toBeVisible()
  })
})
