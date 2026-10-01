import { defineConfig, devices } from '@playwright/test'

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// import dotenv from 'dotenv';
// import path from 'path';
// dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * See https://playwright.dev/docs/test-configuration.
 *
 * Two suites live under ./tests:
 *   - e2e-mocked:     backend is stubbed via page.route('** /api/proxy/**').
 *                     Fast, deterministic, no secrets. Runs per-PR across all
 *                     three rendering engines (chromium/firefox/webkit).
 *   - e2e-integrated: real backend + worker + STT/LLM. Slow, costs money,
 *                     needs cloud credentials. Runs nightly/manual on chromium
 *                     only (one paid transcription run).
 *
 * Select a suite with: npx playwright test --project=<name>
 *
 * The dev server command is env-driven so local runs use `next dev` while the
 * integrated CI workflow can build + start a production server:
 *   PW_WEBSERVER_CMD="npm run build && npm run start" npx playwright test ...
 */

const BASE_URL = 'http://localhost:3000'

export default defineConfig({
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  retries: 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('')`. */
    baseURL: BASE_URL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    /* Mocked suite: all three rendering engines. No paid calls, so cross-browser
       coverage here is cheap. */
    {
      name: 'e2e-mocked-chromium',
      testDir: './tests/e2e-mocked',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'e2e-mocked-firefox',
      testDir: './tests/e2e-mocked',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'e2e-mocked-webkit',
      testDir: './tests/e2e-mocked',
      use: { ...devices['Desktop Safari'] },
    },

    /* Integrated suite: chromium only. Each browser would trigger its own real
       STT/LLM run, so we keep this to a single Chromium-family engine to control
       cost. Cross-browser confidence comes from the mocked suite above. */
    {
      name: 'e2e-integrated',
      testDir: './tests/e2e-integrated',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run the frontend before starting the tests. Command is env-driven (see
     webServerCommand above) so local uses `next dev` and integrated CI can
     build + start a production server.

     Set PW_NO_WEBSERVER=1 to skip this entirely — used in the integrated CI
     workflow where the frontend is already served by docker compose. */
  webServer: process.env.PW_NO_WEBSERVER
    ? undefined
    : {
        command: process.env.PW_WEBSERVER_CMD ?? 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})
