import { test, expect } from "@playwright/test"

const MISSIONARY_EMAIL = process.env.E2E_MISSIONARY_EMAIL ?? "joe.man@spo.org"
const MISSIONARY_PASSWORD = process.env.E2E_MISSIONARY_PASSWORD ?? "Test1234"

// Login tests run WITHOUT stored auth — they test the login page itself.
test.use({ storageState: { cookies: [], origins: [] } })

test.describe("Login", () => {
  test("successful login redirects to dashboard", async ({ page }) => {
    await page.goto("/login")

    await expect(page.getByText("Welcome back")).toBeVisible()
    await expect(page.getByText("Sign in to your DonorCRM account")).toBeVisible()

    await page.getByLabel("Email").fill(MISSIONARY_EMAIL)
    await page.getByLabel("Password").fill(MISSIONARY_PASSWORD)
    await page.getByRole("button", { name: "Sign in" }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL("/", { timeout: 15_000 })
  })

  test("invalid credentials stay on login page", async ({ page }) => {
    await page.goto("/login")

    await page.getByLabel("Email").fill("wrong@example.com")
    await page.getByLabel("Password").fill("WrongPassword")
    await page.getByRole("button", { name: "Sign in" }).click()

    // The 401 response triggers the axios interceptor which navigates back to /login.
    // After the page settles, user should still be on the login page (not authenticated).
    await page.waitForTimeout(3_000)
    await expect(page).toHaveURL(/\/login/)

    // Login form should be visible again
    await expect(page.getByText("Welcome back")).toBeVisible()
  })

  test("sign in button shows loading state while submitting", async ({ page }) => {
    await page.goto("/login")

    await page.getByLabel("Email").fill(MISSIONARY_EMAIL)
    await page.getByLabel("Password").fill(MISSIONARY_PASSWORD)

    const submitButton = page.getByRole("button", { name: "Sign in" })
    await submitButton.click()

    // Button should show "Signing in..." briefly
    await expect(page.getByRole("button", { name: "Signing in..." })).toBeVisible()
  })

  test("login form requires email and password", async ({ page }) => {
    await page.goto("/login")

    // Both fields have required attribute — submitting empty form should not navigate
    await page.getByRole("button", { name: "Sign in" }).click()
    await expect(page).toHaveURL("/login")
  })
})
