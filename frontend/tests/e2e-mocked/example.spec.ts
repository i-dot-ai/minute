import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect } from '@playwright/test'

test('test', async ({ page }) => {
  await mockBackend(page)

  await page.goto('/')
  await page.getByRole('link', { name: 'Transcripts' }).click()

  await expect(page).toHaveURL('/transcriptions')


})
