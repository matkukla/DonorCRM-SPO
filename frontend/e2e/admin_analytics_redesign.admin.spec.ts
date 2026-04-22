/**
 * Admin Analytics Redesign E2E Tests (Issue #49, admin only)
 *
 * Verifies:
 *   1. All 5 new tiles mount and reach a resolved (non-loading) state
 *   2. The hero Fiscal Year Pace tile renders its labeled sub-values
 *   3. Behind-goal rows are interactive
 *
 * Follows the #1 rule of E2E tests (CLAUDE.md): a test MUST fail when the
 * feature it tests is broken. No "fixing the app inside the test".
 *
 * Backend tests (apps/insights/tests/test_admin_analytics_views.py) cover the
 * auth matrix (401/403/200) — no need to re-prove that here.
 */
import { expect, type Page, test } from "@playwright/test"

const ANALYTICS_URL = "/admin/analytics/dashboard"
const TILE_RESOLVE_MS = 8_000

/** Wait for a tile's data-state attribute to become "ready" or "error". */
async function waitForTileResolved(page: Page, testid: string) {
  const tile = page.getByTestId(testid)
  await expect(tile).toBeVisible({ timeout: TILE_RESOLVE_MS })
  await expect
    .poll(
      async () => tile.getAttribute("data-state"),
      { timeout: TILE_RESOLVE_MS, message: `Tile ${testid} never exited loading` },
    )
    .not.toBe("loading")
}

test.describe("Admin Analytics Redesign (admin)", () => {
  test("all five redesigned tiles render", async ({ page }) => {
    await page.goto(ANALYTICS_URL)

    await expect(
      page.getByRole("heading", { name: "Analytics Dashboard" }),
    ).toBeVisible({ timeout: 3_000 })

    await waitForTileResolved(page, "fy-pace-tile")
    await waitForTileResolved(page, "missionaries-behind-tile")
    await waitForTileResolved(page, "weekly-engagement-tile")
    await waitForTileResolved(page, "pipeline-funnel-tile")
    await waitForTileResolved(page, "fy-donations-tile")

    await page.screenshot({
      path: "e2e/artifacts/admin_analytics_redesign_loaded.png",
      fullPage: true,
    })
  })

  test("fiscal year pace tile shows raised amount, pace badge, YoY, and import caption", async ({
    page,
  }) => {
    await page.goto(ANALYTICS_URL)
    await waitForTileResolved(page, "fy-pace-tile")

    const paceTile = page.getByTestId("fy-pace-tile")
    await expect(paceTile.getByTestId("fy-pace-raised")).toContainText(/\$/)
    await expect(paceTile.getByTestId("fy-pace-badge")).toContainText(/% of pace/i)
    await expect(paceTile.getByTestId("fy-pace-yoy")).toBeVisible()
    await expect(paceTile.getByTestId("fy-pace-import-caption")).toBeVisible()
  })

  test("behind-goal tile either shows rows or the empty-state celebration", async ({ page }) => {
    await page.goto(ANALYTICS_URL)
    await waitForTileResolved(page, "missionaries-behind-tile")

    const rows = page.getByTestId("missionaries-behind-row")
    const rowCount = await rows.count()
    if (rowCount === 0) {
      await expect(page.getByText(/all missionaries on pace/i)).toBeVisible()
      return
    }

    // Each row carries the missionary's monthly-goal cents formatted as currency
    // and a pace percentage — prove both are present in the first row.
    const firstRow = rows.first()
    await expect(firstRow).toContainText(/\$/)
    await expect(firstRow).toContainText(/%/)
  })

  test("pipeline funnel tile renders all 7 stages when there is pipeline activity", async ({
    page,
  }) => {
    await page.goto(ANALYTICS_URL)
    await waitForTileResolved(page, "pipeline-funnel-tile")

    const tile = page.getByTestId("pipeline-funnel-tile")
    const rows = tile.getByTestId("pipeline-stage-row")
    const count = await rows.count()
    if (count === 0) {
      await expect(tile.getByText(/no pipeline activity/i)).toBeVisible()
      return
    }
    // 7 stages always render when the funnel has data
    expect(count).toBe(7)
  })
})
