import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect } from '@playwright/test'

const OLD_URL = 'http://minute.i.ai.cabinetoffice.gov.uk:3000'

test.use({
  launchOptions: {
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--host-resolver-rules=MAP minute.i.ai.cabinetoffice.gov.uk 127.0.0.1`,
    ],
  },
})

test('the old URL shows the migration banner on the home page', async ({
  page,
}) => {
  await mockBackend(page)
  await page.goto(`${OLD_URL}/`)

  await expect(
    page.getByRole('heading', { name: /Minute has a new home/ })
  ).toBeVisible()
})

test('the old URL shows the notification banner on the unauthorised page', async ({
  page,
}) => {
  await mockBackend(page)
  await page.goto(`${OLD_URL}/unauthorised`)

  await expect(page.getByText('This is an old Minute address')).toBeVisible()
})

test('the normal URL does not show the migration banner', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: /Minute has a new home/ })
  ).toHaveCount(0)
})
