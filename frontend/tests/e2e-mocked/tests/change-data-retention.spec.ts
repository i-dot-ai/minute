import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { json } from '@/tests/e2e-mocked/utilities/routes/general'
import { usersMe } from '@/tests/e2e-mocked/mocked-responses/users.me'
import { test, expect } from '@playwright/test'

test('changing the data retention period updates the transcriptions page', async ({
  page,
}) => {
  await mockBackend(page)

  await page.goto('/')
  await page.getByRole('link', { name: 'transcriptions' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  await expect(
    page.getByText('Transcriptions will be kept indefinitely')
  ).toBeVisible()

  await page
    .getByRole('button', { name: 'Change data retention period' })
    .click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Data retention period' })
  ).toBeVisible()

  const patchRequest = page.waitForRequest(
    (req) =>
      req.method() === 'PATCH' && /\/users\/data-retention$/.test(req.url())
  )

  await dialog.getByRole('radio', { name: '7 days' }).check()
  await dialog.getByRole('button', { name: 'Save' }).click()

  const patch = await patchRequest
  expect(patch.postDataJSON()).toEqual({ data_retention_days: 7 })

  await expect(dialog).toBeHidden()
  await expect(
    page.getByText('Transcriptions will be deleted after 7 days')
  ).toBeVisible()
})

test('businessandtrade users get the fixed settings', async ({ page }) => {
  await mockBackend(page)
  await page.route('**/api/proxy/users/me', (route) =>
    route.fulfill(
      json(200, { ...usersMe, email: 'jane@businessandtrade.gov.uk' })
    )
  )

  await page.goto('/transcriptions')
  await expect(
    page.getByRole('button', { name: 'Change data retention period' })
  ).not.toBeVisible()

  await expect(
    page.getByText('This has been set by your department and cannot be changed')
  ).toBeVisible()
})
