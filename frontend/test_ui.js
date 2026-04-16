const { chromium } = require('playwright');

const CHROMIUM_PATH = '/home/matkukla/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROMIUM_PATH,
    headless: true,
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = [];
  const log = (msg) => { results.push(msg); console.log(msg); };

  try {
    // 1. Login
    log('--- Test 1: Login ---');
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"], input[name="email"]', 'matthew.kukla@spo.org');
    await page.fill('input[type="password"], input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard**', { timeout: 8000 }).catch(() => {});
    log(`After login URL: ${page.url()}`);

    // 2. Navigate to Contacts list
    log('--- Test 2: Contacts list with checkboxes ---');
    await page.goto('http://localhost:5173/contacts');
    await page.waitForSelector('table', { timeout: 8000 });
    const checkboxCount = await page.locator('input[type="checkbox"]').count();
    log(`Checkboxes in contacts table: ${checkboxCount}`);

    // Check for select-all checkbox in header
    const headerCheckbox = await page.locator('thead input[type="checkbox"]').count();
    log(`Header (select-all) checkboxes: ${headerCheckbox}`);

    // Click the first row checkbox
    const firstRowCheckbox = page.locator('tbody input[type="checkbox"]').first();
    if (await firstRowCheckbox.count() > 0) {
      await firstRowCheckbox.click();
      log('Clicked first row checkbox');
      // Check for bulk action bar
      const bulkBar = await page.locator('text=selected').first().textContent().catch(() => null);
      log(`Bulk action bar text: ${bulkBar}`);
      const addToGroupBtn = await page.locator('text=Add to Group').count();
      log(`"Add to Group" button visible: ${addToGroupBtn > 0}`);
    }

    // 3. Add Contact form with GroupPicker
    log('--- Test 3: Add Contact form ---');
    await page.goto('http://localhost:5173/contacts/new');
    await page.waitForSelector('h1', { timeout: 5000 });
    const groupsCard = await page.locator('text=Groups').count();
    log(`Groups card visible on Add Contact form: ${groupsCard > 0}`);
    const groupPickerBtn = await page.locator('button:has-text("Select groups")').count();
    log(`GroupPicker button visible: ${groupPickerBtn > 0}`);

    // 4. Navigate to a Group detail page
    log('--- Test 4: Group detail ---');
    await page.goto('http://localhost:5173/groups');
    await page.waitForSelector('table, [class*="card"], text=Groups', { timeout: 8000 });
    // Click first group
    const firstGroup = page.locator('a[href*="/groups/"], tr').first();
    const groupLink = page.locator('a[href*="/groups/"]').first();
    if (await groupLink.count() > 0) {
      await groupLink.click();
      await page.waitForSelector('text=Contacts in this Group', { timeout: 5000 });
      log(`Group detail page loaded: ${page.url()}`);
      const addContactsBtn = await page.locator('button:has-text("Add Contacts")').count();
      log(`"Add Contacts" button on group detail: ${addContactsBtn > 0}`);
    } else {
      log('No group links found on groups page');
    }

    log('--- All tests complete ---');
  } catch (err) {
    log(`ERROR: ${err.message}`);
  }

  await browser.close();
  console.log('\nRESULTS:\n' + results.join('\n'));
})();
