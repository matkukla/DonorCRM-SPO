import { test, expect, type Page } from "@playwright/test"

const BASE_URL = process.env.BASE_URL || "http://localhost:5173"
const EMAIL = process.env.E2E_EMAIL
const PASSWORD = process.env.E2E_PASSWORD
const JOURNAL_WITH_CONTACTS_ID = process.env.E2E_JOURNAL_ID

if (!EMAIL) throw new Error("E2E_EMAIL env var is required")
if (!PASSWORD) throw new Error("E2E_PASSWORD env var is required")
if (!JOURNAL_WITH_CONTACTS_ID) throw new Error("E2E_JOURNAL_ID env var is required")

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByLabel("Email").fill(EMAIL)
  await page.getByLabel("Password").fill(PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15_000 })
}

test.describe("Journal feature", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test("journals list page loads", async ({ page }) => {
    await page.goto(`${BASE_URL}/journals`)
    await expect(page.getByRole("heading", { name: "Journals" })).toBeVisible({ timeout: 10_000 })
    // Either journal cards or the empty state — but no error banner
    await expect(page.getByText("Failed to load journals")).not.toBeVisible()
    // At least one journal card or empty-state should render
    const journalCard = page.locator(".grid > div").first()
    const emptyState = page.getByText("No journals yet")
    await expect(journalCard.or(emptyState)).toBeVisible({ timeout: 10_000 })
  })

  test("journal detail page renders the pipeline grid", async ({ page }) => {
    await page.goto(`${BASE_URL}/journals/${JOURNAL_WITH_CONTACTS_ID}`)

    // The pipeline grid table should appear (this journal has contacts)
    const gridTable = page.getByRole("table", { name: "Journal grid" })
    await expect(gridTable).toBeVisible({ timeout: 10_000 })

    // Header columns should be present (two "Contact" headers exist: sticky name column + stage column)
    await expect(page.getByRole("columnheader", { name: "Contact" }).first()).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "Decision" })).toBeVisible()

    // At least one data row should exist
    const dataRows = gridTable.getByRole("row")
    // Header row + at least 1 data row
    await expect(dataRows.nth(1)).toBeVisible()
  })

  test("stage cell toggle: unchecked → checked → unchecked", async ({ page }) => {
    await page.goto(`${BASE_URL}/journals/${JOURNAL_WITH_CONTACTS_ID}`)

    const gridTable = page.getByRole("table", { name: "Journal grid" })
    await expect(gridTable).toBeVisible({ timeout: 10_000 })

    // Find the first unchecked stage cell
    const uncheckedCell = gridTable
      .getByRole("button", { name: /Click to mark complete/i })
      .first()
    await expect(uncheckedCell).toBeVisible({ timeout: 10_000 })

    // --- Check (creates a stage event) ---
    await uncheckedCell.click()

    // Spinner may briefly appear; then the checked button should become visible
    const checkedCell = gridTable
      .getByRole("button", { name: /Click to uncheck/i })
      .first()
    await expect(checkedCell).toBeVisible({ timeout: 10_000 })

    // --- Uncheck (deletes stage events) ---
    await checkedCell.click()

    // Cell should revert to unchecked state
    await expect(
      gridTable.getByRole("button", { name: /Click to mark complete/i }).first()
    ).toBeVisible({ timeout: 10_000 })
  })

  test("Add Contacts button opens the dialog", async ({ page }) => {
    await page.goto(`${BASE_URL}/journals/${JOURNAL_WITH_CONTACTS_ID}`)

    // The Add Contacts button should be present
    const addContactsButton = page.getByRole("button", { name: /Add Contacts/i })
    await expect(addContactsButton).toBeVisible({ timeout: 10_000 })

    // Click to open
    await addContactsButton.click()

    // Dialog with correct title should appear
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 })
    await expect(
      page.getByRole("heading", { name: "Add Contacts to Journal" })
    ).toBeVisible()

    // Search input should be present
    await expect(page.getByLabel("Search Contacts")).toBeVisible()

    // Dismiss via Escape
    await page.keyboard.press("Escape")
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 5_000 })
  })

  test("Reports tab renders without errors", async ({ page }) => {
    await page.goto(`${BASE_URL}/journals/${JOURNAL_WITH_CONTACTS_ID}`)

    // Click the Reports tab
    const reportsTab = page.getByRole("tab", { name: /Reports/i })
    await expect(reportsTab).toBeVisible({ timeout: 10_000 })
    await reportsTab.click()

    // Tab should become active
    await expect(reportsTab).toHaveAttribute("data-state", "active")

    // No error message should appear
    await expect(page.getByText("Failed to load journal")).not.toBeVisible()

    // The tab panel content area should be in the DOM without a crash
    // (Reports may show charts or empty states — either is acceptable)
    const tabPanel = page.getByRole("tabpanel")
    await expect(tabPanel).toBeVisible({ timeout: 10_000 })
  })
})
