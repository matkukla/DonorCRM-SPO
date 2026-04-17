/**
 * Analytics Dashboard E2E Tests (admin only)
 *
 * Verifies:
 * 1. Load performance — heading visible within 3s (page-interactive); full data within 8s
 * 2. UserComparison panel — exits loading state and shows user selectors
 * 3. AlertsPanel — exits loading state and shows either alerts or "All clear" message
 * 4. Regression checks — /contacts, /donations, /tasks still load correctly
 *
 * The 3-second target measures page-interactive (heading rendered), not full data render.
 * Full data render (all panels) is asserted under 8 seconds, which accounts for
 * API calls, React hydration, and lazy Suspense boundaries in a Playwright browser.
 */

import { test, expect, type Page, type ConsoleMessage } from "@playwright/test"

const ANALYTICS_URL = "/admin/analytics/dashboard"

// Time from navigation to heading visible — the "page-interactive" SLA
const PAGE_INTERACTIVE_MS = 3_000

// Time from navigation to all data panels resolved — the "full render" SLA.
// Set to 8s to match the JSDoc above. Real observed time in an isolated run
// is ~6-7s; the 8s ceiling provides ~1-2s of regression headroom without
// masking genuine slowdowns.
const FULL_DATA_RENDER_MS = 8_000

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Wait for the analytics page heading to be visible.
 * This confirms the route resolved and the React component mounted.
 */
async function waitForPageInteractive(page: Page): Promise<number> {
  const start = Date.now()
  await expect(
    page.getByRole("heading", { name: "Analytics Dashboard" })
  ).toBeVisible({ timeout: PAGE_INTERACTIVE_MS })
  return Date.now() - start
}

/**
 * Wait for the overview summary cards to show real data values.
 * The card headers (e.g. "Total Contacts") render inside Card components
 * only after the overview API resolves and the skeleton is replaced.
 */
async function waitForOverviewData(page: Page) {
  // Scope to the summary stats grid to avoid matching "Total Contacts" inside
  // the UserComparison metrics table, which can render earlier/independently.
  const summaryGrid = page.locator('[data-testid="summary-stats-grid"]')
  if (await summaryGrid.count() > 0) {
    await expect(
      summaryGrid.getByText("Total Contacts").first()
    ).toBeVisible({ timeout: FULL_DATA_RENDER_MS })
  } else {
    // Fallback: wait for at least one stat card value to appear. Stat card
    // values are numbers (e.g. "42"), rendered only after the API resolves.
    await expect(
      page.locator('[class*="text-3xl"], [class*="text-2xl"]').first()
    ).toBeVisible({ timeout: FULL_DATA_RENDER_MS })
  }
}

/**
 * Wait for the UserComparison card to exit its skeleton/loading state.
 * When data is ready: heading visible + "Missionary 1" label visible.
 */
async function waitForUserComparisonReady(page: Page) {
  await expect(
    page.getByRole("heading", { name: "Compare Missionaries" })
  ).toBeVisible({ timeout: FULL_DATA_RENDER_MS })

  await expect(
    page.getByText("Missionary 1", { exact: true })
  ).toBeVisible({ timeout: FULL_DATA_RENDER_MS })
}

/**
 * Wait for AlertsPanel to exit its loading skeleton.
 * When resolved it shows either alert items or an "All clear" message.
 */
async function waitForAlertsPanelReady(page: Page) {
  await expect(
    page.getByRole("heading", { name: "Coaching Alerts" })
  ).toBeVisible({ timeout: FULL_DATA_RENDER_MS })

  // Must show resolved content — either "All clear" or an alert body text
  await expect(
    page.getByText(/All clear|contacts stalled|conversion rate|active journals/i).first()
  ).toBeVisible({ timeout: FULL_DATA_RENDER_MS })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Analytics Dashboard (admin)", () => {
  test("page-interactive within 3 seconds; full data render within 8 seconds", async ({
    page,
  }) => {
    const errors: string[] = []
    const consoleListener = (msg: ConsoleMessage) => {
      if (msg.type() === "error") errors.push(msg.text())
    }
    page.on("console", consoleListener)

    const navStart = Date.now()

    await page.goto(ANALYTICS_URL)

    // ── Measure time to page-interactive ──────────────────────────────────
    const interactiveMs = await waitForPageInteractive(page)

    // ── Wait for overview summary card data ───────────────────────────────
    await waitForOverviewData(page)

    // ── Wait for UserComparison panel ─────────────────────────────────────
    await waitForUserComparisonReady(page)

    // ── Wait for AlertsPanel ──────────────────────────────────────────────
    await waitForAlertsPanelReady(page)

    const totalMs = Date.now() - navStart
    page.off("console", consoleListener)

    // ── Screenshot at fully-loaded state ──────────────────────────────────
    await page.screenshot({
      path: "e2e/artifacts/analytics_dashboard_loaded.png",
      fullPage: true,
    })

    // ── Assertions ────────────────────────────────────────────────────────

    // Page must be interactive (heading visible) within 3 seconds
    expect(
      interactiveMs,
      `Page-interactive took ${interactiveMs}ms — must be under ${PAGE_INTERACTIVE_MS}ms`
    ).toBeLessThan(PAGE_INTERACTIVE_MS)

    // All panels must fully render within 8 seconds
    expect(
      totalMs,
      `Full data render took ${totalMs}ms — must be under ${FULL_DATA_RENDER_MS}ms`
    ).toBeLessThan(FULL_DATA_RENDER_MS)

    // Log timing for CI visibility
    console.log(`[perf] page-interactive: ${interactiveMs}ms | full render: ${totalMs}ms`)

    // No actionable JS errors
    const actionableErrors = errors.filter(
      (e) =>
        !e.includes("favicon") &&
        !e.includes("ERR_BLOCKED_BY_CLIENT") &&
        !e.includes("net::ERR_ABORTED")
    )
    expect(
      actionableErrors,
      `Browser console errors: ${actionableErrors.join(" | ")}`
    ).toHaveLength(0)
  })

  test("UserComparison panel — exits loading and shows user selectors", async ({
    page,
  }) => {
    await page.goto(ANALYTICS_URL)
    await waitForUserComparisonReady(page)

    // Once data arrives, the pulse skeleton must be gone from the Compare card
    // Locate the card by its heading, go up to the card container, check for skeletons
    const compareHeading = page.getByRole("heading", { name: "Compare Missionaries" })
    // The card wraps the heading — go up two DOM levels (CardHeader > Card)
    const card = compareHeading.locator("..").locator("..")
    await expect(card.locator(".animate-pulse")).toHaveCount(0, {
      timeout: FULL_DATA_RENDER_MS,
    })

    // Both "Missionary N" labels must exist (the select dropdowns)
    await expect(page.getByText("Missionary 1", { exact: true })).toBeVisible()
    await expect(page.getByText("Missionary 2", { exact: true })).toBeVisible()

    await page.screenshot({ path: "e2e/artifacts/user_comparison_panel.png" })
  })

  test("AlertsPanel — exits loading and shows resolved content", async ({
    page,
  }) => {
    await page.goto(ANALYTICS_URL)
    await waitForAlertsPanelReady(page)

    // Coaching Alerts card must have no loading skeletons once data resolved
    const alertsHeading = page.getByRole("heading", { name: "Coaching Alerts" })
    const alertsCard = alertsHeading.locator("..").locator("..")
    await expect(alertsCard.locator(".animate-pulse")).toHaveCount(0, {
      timeout: FULL_DATA_RENDER_MS,
    })

    await page.screenshot({ path: "e2e/artifacts/alerts_panel.png" })
  })

  test("UserComparison — selecting two users shows comparison metrics", async ({
    page,
  }) => {
    await page.goto(ANALYTICS_URL)
    await waitForUserComparisonReady(page)

    // The UserComparison component has two comboboxes (Missionary 1 and 2)
    // Find them scoped inside the "Compare Missionaries" card
    const compareHeading = page.getByRole("heading", { name: "Compare Missionaries" })
    const card = compareHeading.locator("..").locator("..")

    const triggers = card.getByRole("combobox")

    // Scroll the card into the center of the viewport so Radix Select portals
    // open within visible bounds (not above/below the viewport edge).
    await card.scrollIntoViewIfNeeded()
    await page.mouse.wheel(0, -200)
    await page.waitForTimeout(200)

    // Select first available user for Missionary 1
    await triggers.nth(0).click()
    await page.waitForSelector('[role="listbox"]', { timeout: 3_000 })
    const options1 = page.locator('[role="option"]')
    await expect(options1.first()).toBeVisible({ timeout: 3_000 })
    const firstOptionText = await options1.first().textContent()
    await options1.first().click()
    await page.waitForTimeout(300)

    // Select a different user for Missionary 2.
    // Radix marks the already-selected user (Missionary 1's choice) as aria-disabled
    // in the second dropdown. Pick the first option that is not aria-disabled.
    await triggers.nth(1).click()
    await page.waitForSelector('[role="listbox"]', { timeout: 3_000 })
    const enabledOption = page.locator('[role="option"]:not([aria-disabled="true"])').first()
    await expect(enabledOption).toBeVisible({ timeout: 3_000 })
    await enabledOption.click()

    // Comparison metrics table should now be visible — scope to the card to avoid
    // strict-mode violations (same labels appear in the summary cards above).
    await expect(card.getByText("Total Contacts", { exact: true }).first()).toBeVisible({ timeout: 3_000 })
    await expect(card.getByText("Active Journals", { exact: true }).first()).toBeVisible()
    await expect(card.getByText("Conversion Rate", { exact: true }).first()).toBeVisible()

    await page.screenshot({ path: "e2e/artifacts/user_comparison_metrics.png" })

    expect(firstOptionText?.trim().length).toBeGreaterThan(0)
  })
})

// Regression page load SLA. Conservative at 8s to tolerate parallel-worker
// CPU contention when all 9 tests run simultaneously. Observed isolated times
// are 2-4s. A real regression (server crash, broken route) would exceed 8s.
const REGRESSION_PAGE_MS = 8_000

test.describe("Regression — other pages still work (admin)", () => {
  test("/contacts list loads", async ({ page }) => {
    const errors: string[] = []
    const listener = (msg: ConsoleMessage) => {
      if (msg.type() === "error") errors.push(msg.text())
    }
    page.on("console", listener)

    const start = Date.now()
    await page.goto("/contacts")
    await expect(page.getByRole("heading", { name: /contacts/i })).toBeVisible({
      timeout: REGRESSION_PAGE_MS,
    })
    const elapsed = Date.now() - start
    page.off("console", listener)

    console.log(`[perf] /contacts load: ${elapsed}ms`)
    await page.screenshot({ path: "e2e/artifacts/contacts_regression.png" })

    expect(elapsed).toBeLessThan(REGRESSION_PAGE_MS)

    const actionableErrors = errors.filter(
      (e) => !e.includes("favicon") && !e.includes("ERR_BLOCKED_BY_CLIENT")
    )
    expect(actionableErrors, `Console errors: ${actionableErrors.join(" | ")}`).toHaveLength(0)
  })

  test("/donations list loads", async ({ page }) => {
    const errors: string[] = []
    const listener = (msg: ConsoleMessage) => {
      if (msg.type() === "error") errors.push(msg.text())
    }
    page.on("console", listener)

    const start = Date.now()
    await page.goto("/donations")
    await expect(page.getByRole("heading", { name: /donations/i })).toBeVisible({
      timeout: REGRESSION_PAGE_MS,
    })
    const elapsed = Date.now() - start
    page.off("console", listener)

    console.log(`[perf] /donations load: ${elapsed}ms`)
    await page.screenshot({ path: "e2e/artifacts/donations_regression.png" })

    expect(elapsed).toBeLessThan(REGRESSION_PAGE_MS)

    const actionableErrors = errors.filter(
      (e) => !e.includes("favicon") && !e.includes("ERR_BLOCKED_BY_CLIENT")
    )
    expect(actionableErrors, `Console errors: ${actionableErrors.join(" | ")}`).toHaveLength(0)
  })

  test("/tasks list loads", async ({ page }) => {
    const errors: string[] = []
    const listener = (msg: ConsoleMessage) => {
      if (msg.type() === "error") errors.push(msg.text())
    }
    page.on("console", listener)

    const start = Date.now()
    await page.goto("/tasks")
    await expect(page.getByRole("heading", { name: /tasks/i })).toBeVisible({
      timeout: REGRESSION_PAGE_MS,
    })
    const elapsed = Date.now() - start
    page.off("console", listener)

    console.log(`[perf] /tasks load: ${elapsed}ms`)
    await page.screenshot({ path: "e2e/artifacts/tasks_regression.png" })

    expect(elapsed).toBeLessThan(REGRESSION_PAGE_MS)

    const actionableErrors = errors.filter(
      (e) => !e.includes("favicon") && !e.includes("ERR_BLOCKED_BY_CLIENT")
    )
    expect(actionableErrors, `Console errors: ${actionableErrors.join(" | ")}`).toHaveLength(0)
  })
})
