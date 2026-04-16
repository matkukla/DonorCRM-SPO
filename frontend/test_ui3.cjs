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

  await page.goto('http://localhost:5173/login');
  await page.waitForSelector('input[type="email"]');
  await page.fill('input[type="email"]', 'matthew.kukla@spo.org');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  await page.goto('http://localhost:5173/contacts');
  await page.waitForTimeout(5000); // wait for full data load

  const tableHtml = await page.locator('table').innerHTML().catch(() => 'no table');
  console.log('Table HTML (first 1000 chars):\n', tableHtml.substring(0, 1000));

  const allInputs = await page.locator('table input').all();
  console.log('\nAll inputs in table:', allInputs.length);
  for (const inp of allInputs.slice(0, 5)) {
    const type = await inp.getAttribute('type');
    const inHead = await inp.evaluate(el => !!el.closest('thead'));
    const inBody = await inp.evaluate(el => !!el.closest('tbody'));
    console.log(`  type=${type} inThead=${inHead} inTbody=${inBody}`);
  }

  await browser.close();
})();
