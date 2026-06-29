import { test, expect, type Page } from "@playwright/test"

/**
 * E2E for issue #166: on the Goal page, clicking "Save Settings" with one or
 * more journals checked overwrites "Monthly Goal ($)" with the straight sum of
 * those journals' (monthly) goal_amounts.
 *
 * The test computes the expected sum from the live API rather than a hardcoded
 * fixture, so it fails if the feature stops summing — not merely if the seed
 * data changes. It needs an account that owns at least one journal with a goal.
 */

const BASE_URL = process.env.BASE_URL || "http://localhost:5173"
const API_URL = process.env.E2E_API_URL || "http://localhost:8000/api/v1"
const EMAIL = process.env.E2E_EMAIL
const PASSWORD = process.env.E2E_PASSWORD

if (!EMAIL) throw new Error("E2E_EMAIL env var is required")
if (!PASSWORD) throw new Error("E2E_PASSWORD env var is required")

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByLabel("Email").fill(EMAIL)
  await page.getByLabel("Password").fill(PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15_000 })
}

test.describe("Goal page — auto-populate Monthly Goal from journals", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test("Save Settings overwrites Monthly Goal with the sum of checked journals", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/goal`)
    await expect(page.getByRole("heading", { name: "Support Goal" })).toBeVisible({
      timeout: 10_000,
    })

    // The journal checkbox list only renders when the user owns journals.
    const journalSection = page.getByText("Track Progress By Journals")
    await expect(journalSection).toBeVisible({ timeout: 10_000 })

    // Read the authenticated user's journals (with goal_amount) straight from the
    // API using the browser's stored token, so we know the expected sum.
    const journals: { id: string; name: string; goal_amount: string | null }[] =
      await page.evaluate(async (api) => {
        const token = localStorage.getItem("donorcrm_access_token")
        const res = await fetch(`${api}/journals/?page_size=100`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        return data.results
      }, API_URL)

    // Pick journals that have a numeric monthly goal to check.
    const withGoals = journals.filter(
      (j) => j.goal_amount != null && !Number.isNaN(parseFloat(j.goal_amount))
    )
    test.skip(withGoals.length === 0, "account has no journals with a goal_amount")

    const expectedCents = withGoals.reduce(
      (sum, j) => sum + Math.round(parseFloat(j.goal_amount as string) * 100),
      0
    )
    const expectedDollars = expectedCents / 100

    // Type a deliberately-wrong manual value that the sum must overwrite.
    const goalInput = page.getByLabel("Monthly Goal ($)")
    await goalInput.fill("999999")

    // Check each journal with a goal.
    for (const j of withGoals) {
      await page.getByLabel(j.name, { exact: true }).check()
    }

    await page.getByRole("button", { name: /save settings/i }).click()

    // Saved confirmation appears, and the input now shows the summed total.
    await expect(page.getByText("Saved")).toBeVisible({ timeout: 10_000 })
    await expect(goalInput).toHaveValue(String(expectedDollars))
  })
})
