import { defineConfig, devices } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const MISSIONARY_STORAGE = path.resolve(__dirname, "e2e/.auth/missionary.json")
const ADMIN_STORAGE = path.resolve(__dirname, "e2e/.auth/admin.json")

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",

  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    // Auth setup — runs first, saves browser storage state
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },

    // Tests that run as an authenticated missionary
    {
      name: "missionary",
      use: {
        ...devices["Desktop Chrome"],
        storageState: MISSIONARY_STORAGE,
      },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },

    // Tests that run as an authenticated admin (opt-in via filename)
    {
      name: "admin",
      use: {
        ...devices["Desktop Chrome"],
        storageState: ADMIN_STORAGE,
      },
      dependencies: ["setup"],
      testMatch: /\.admin\.spec\.ts/,
    },
  ],

  webServer: [
    {
      command: "bash -c 'cd .. && source venv/bin/activate && python manage.py runserver 8000'",
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
  ],
})
