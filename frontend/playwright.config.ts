import { defineConfig, devices } from '@playwright/test'

/**
 * See https://playwright.dev/docs/test-configuration.
 *
 * Two suites live under ./tests:
 *   - e2e-mocked:     backend stubbed via page.route. Runs per-PR across
 *                     chromium/firefox/webkit.
 *   - e2e-integrated: real backend + worker + STT/LLM. Chromium only, manual.
 *
 * Select a suite with: npx playwright test --project=<name>
 */

const BASE_URL = 'http://localhost:3000'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: 'html',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'e2e-mocked',
      testDir: './tests/e2e-mocked',
      use: {
        ...devices['Desktop Chrome'],
        permissions: ['microphone'],
        launchOptions: {
          args: [
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
          ],
        },
      },
    },
    {
      name: 'e2e-integrated',
      testDir: './tests/e2e-integrated',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Set PW_NO_WEBSERVER=1 to skip (integrated CI serves the frontend via docker).
  webServer: process.env.PW_NO_WEBSERVER
    ? undefined
    : {
        command: process.env.PW_WEBSERVER_CMD ?? 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})
