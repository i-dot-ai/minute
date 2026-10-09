import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect } from '@playwright/test'

test('changing the data retention period updates the transcriptions page', async ({
  page,
}) => {
  await mockBackend(page)

  await page.goto('/')
  await page.getByRole('link', { name: 'transcripts' }).click()
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
