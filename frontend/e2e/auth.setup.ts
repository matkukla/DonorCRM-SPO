import { test as setup, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const MISSIONARY_STORAGE = path.resolve(__dirname, ".auth/missionary.json")
const ADMIN_STORAGE = path.resolve(__dirname, ".auth/admin.json")

/**
 * Authenticate as a missionary user and save browser state.
 * Uses the test account created by `python manage.py create_test_accounts`.
 */
setup("authenticate as missionary", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("Email").fill("joe.man@spo.org")
  await page.getByLabel("Password").fill("Test1234")
  await page.getByRole("button", { name: "Sign in" }).click()

  // Wait for redirect to dashboard
  await expect(page).toHaveURL("/", { timeout: 15_000 })

  await page.context().storageState({ path: MISSIONARY_STORAGE })
})

/**
 * Authenticate as an admin user and save browser state.
 */
setup("authenticate as admin", async ({ page }) => {
  await page.goto("/login")
  await page.getByLabel("Email").fill("alex.becker@spo.org")
  await page.getByLabel("Password").fill("Test1234")
  await page.getByRole("button", { name: "Sign in" }).click()

  await expect(page).toHaveURL("/", { timeout: 15_000 })

  await page.context().storageState({ path: ADMIN_STORAGE })
})
