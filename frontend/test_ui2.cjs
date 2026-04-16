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

  // Capture all network requests
  const apiRequests = [];
  page.on('response', async (resp) => {
    const url = resp.url();
    if (url.includes('/api/')) {
      const status = resp.status();
      apiRequests.push({ url: url.replace('http://localhost:8000', ''), status });
    }
  });

  // Login
  await page.goto('http://localhost:5173/login');
  await page.waitForSelector('input[type="email"]', { timeout: 8000 });
  await page.fill('input[type="email"]', 'matthew.kukla@spo.org');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  console.log('After login URL:', page.url());
  console.log('API calls after login:', apiRequests.slice(-5));

  // Go to contacts
  apiRequests.length = 0;
  await page.goto('http://localhost:5173/contacts');
  await page.waitForTimeout(4000);

  console.log('\nAPI calls on contacts page:');
  apiRequests.forEach(r => console.log(`  ${r.status} ${r.url}`));

  // Check what's actually in the DOM
  const bodyText = await page.locator('body').textContent();
  const hasTable = await page.locator('table').count();
  const hasPulse = await page.locator('.animate-pulse').count();
  console.log('\nhas table:', hasTable, 'has skeleton:', hasPulse);
  console.log('body snippet:', bodyText.substring(0, 300));

  await browser.close();
})();
