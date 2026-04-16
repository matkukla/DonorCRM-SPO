const { chromium } = require('playwright');

const CHROMIUM_PATH = '/home/matkukla/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROMIUM_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  const log = (msg) => console.log(msg);
  let passed = 0, failed = 0;

  const check = (label, condition) => {
    if (condition) { log(`  ✓ ${label}`); passed++; }
    else { log(`  ✗ ${label}`); failed++; }
  };

  try {
    // Login
    log('\n[1] Login');
    await page.goto('http://localhost:5173/login');
    await page.waitForSelector('input[type="email"]', { timeout: 8000 });
    await page.fill('input[type="email"]', 'matthew.kukla@spo.org');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard**', { timeout: 8000 }).catch(() => {});
    check('Redirected away from login', !page.url().includes('/login'));

    // Contacts list - row selection
    log('\n[2] Contacts list row selection');
    await page.goto('http://localhost:5173/contacts');
    // Wait for actual data rows (not skeleton)
    await page.waitForSelector('tbody tr td:not(:has(.animate-pulse))', { timeout: 15000 });
    await page.waitForTimeout(500);

    const headerCb = await page.locator('thead input[type="checkbox"]').count();
    check('Select-all checkbox in header', headerCb === 1);

    const rowCbs = await page.locator('tbody input[type="checkbox"]').count();
    check(`Row checkboxes rendered (got ${rowCbs})`, rowCbs > 0);

    if (rowCbs > 0) {
      await page.locator('tbody input[type="checkbox"]').first().click();
      await page.waitForTimeout(300);
      const bulkText = await page.locator('text=/\\d+ contact/').first().textContent().catch(() => null);
      check(`Bulk action bar shows count ("${bulkText}")`, !!bulkText);
      const addToGroupBtn = await page.locator('button:has-text("Add to Group")').count();
      check('"Add to Group" button appears', addToGroupBtn > 0);

      // Open Add to Group dialog
      if (addToGroupBtn > 0) {
        await page.locator('button:has-text("Add to Group")').click();
        await page.waitForTimeout(500);
        const dialogOpen = await page.locator('[role="dialog"]').count();
        check('Add to Group dialog opens', dialogOpen > 0);
        // Close it
        await page.keyboard.press('Escape');
      }

      // Deselect
      await page.locator('tbody input[type="checkbox"]').first().click();
      await page.waitForTimeout(200);
      const bulkGone = await page.locator('text=/\\d+ contact/').count();
      check('Bulk action bar disappears after deselect', bulkGone === 0);
    }

    // Select-all test
    await page.locator('thead input[type="checkbox"]').first().click();
    await page.waitForTimeout(300);
    const bulkAfterAll = await page.locator('text=/\\d+ contact/').first().textContent().catch(() => null);
    check(`Select-all triggers bulk bar ("${bulkAfterAll}")`, !!bulkAfterAll);

    // Add Contact form - GroupPicker
    log('\n[3] Add Contact form — GroupPicker');
    await page.goto('http://localhost:5173/contacts/new');
    await page.waitForSelector('h1', { timeout: 5000 });
    await page.waitForTimeout(500);

    const formH1 = await page.locator('h1').textContent();
    check('Add Contact form loaded', formH1?.includes('Add Contact'));

    const groupsCard = await page.locator('text=Groups').count();
    check('Groups card visible', groupsCard > 0);

    const selectGroupsBtn = await page.locator('button:has-text("Select groups")').count();
    check('GroupPicker button renders', selectGroupsBtn > 0);

    if (selectGroupsBtn > 0) {
      await page.locator('button:has-text("Select groups")').click();
      await page.waitForTimeout(400);
      // Check popover content appears
      const groupItems = await page.locator('[role="dialog"] button, [data-radix-popper-content-wrapper] button').count();
      check(`GroupPicker popover opens with items (${groupItems})`, groupItems > 0);
      await page.keyboard.press('Escape');
    }

    // Group detail - Add Contacts button
    log('\n[4] Group detail — Add Contacts button');
    // Navigate directly — groups use navigate(), not <a href>
    const TEST_GROUP_ID = 'e2e1cac9-d227-4e07-997c-2e024ed77079';
    await page.goto(`http://localhost:5173/groups/${TEST_GROUP_ID}`);
    await page.waitForSelector('text=Contacts in this Group', { timeout: 8000 });
    log(`  Group detail: ${page.url()}`);
    check('Group detail page loaded', page.url().includes(TEST_GROUP_ID));

    const addBtn = await page.locator('button:has-text("Add Contacts")').count();
    check('"Add Contacts" button present on group detail', addBtn > 0);

    if (addBtn > 0) {
      await page.locator('button:has-text("Add Contacts")').click();
      await page.waitForTimeout(500);
      const dialog = await page.locator('[role="dialog"]').count();
      check('Add Contacts dialog opens', dialog > 0);

      const searchInput = await page.locator('[role="dialog"] input').count();
      check('Search input in dialog', searchInput > 0);

      const dialogTitle = await page.locator('[role="dialog"] [class*="Title"], [role="dialog"] h2').first().textContent().catch(() => '');
      check(`Dialog title correct ("${dialogTitle?.trim()}")`, dialogTitle?.includes('Add Contacts'));

      if (searchInput > 0) {
        await page.locator('[role="dialog"] input').first().fill('a');
        await page.waitForTimeout(600);
        const contactResults = await page.locator('[role="dialog"] .flex').count();
        check(`Contact search returns results (${contactResults} elements)`, contactResults > 0);
      }

      await page.keyboard.press('Escape');
    }

  } catch (err) {
    log(`\nFATAL ERROR: ${err.message}`);
    failed++;
  }

  await browser.close();
  log(`\n${'─'.repeat(40)}`);
  log(`Results: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
})();
