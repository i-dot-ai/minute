import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
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

  await page.getByRole('link', { name: 'your account settings' }).click()

  await expect(page).toHaveURL('/profile#settings')
  await expect(
    page.getByRole('cell', { name: 'Transcriptions will be kept indefinitely' })
  ).toBeVisible()
  await page.getByRole('button', { name: 'Change data retention' }).click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Data retention period' })
  ).toBeVisible()

  await dialog.getByRole('radio', { name: '7 days' }).check()
  await dialog.getByRole('button', { name: 'Save' }).click()

  await expect(dialog).toBeHidden()
  await expect(
    page.getByRole('cell', {
      name: 'Transcriptions will be deleted after 7 days',
    })
  ).toBeVisible()
  await page.getByRole('link', { name: 'transcriptions' }).click()
  await expect(
    page.getByText('Transcriptions will be deleted after 7 days')
  ).toBeVisible()
})
