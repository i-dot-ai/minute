import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect } from '@playwright/test'

test('denied microphone access shows the problem banner and instructions', async ({
  page,
}) => {
  await mockBackend(page)
  await page.addInitScript(() => {
    navigator.permissions.query = async () =>
      ({ state: 'denied', addEventListener() {} }) as unknown as PermissionStatus
  })

  await page.goto('/')

  await expect(page.getByText('There is a problem.')).toBeVisible()
  await expect(
    page.getByText('Microphone access has not been given')
  ).toBeVisible()
  await expect(
    page.getByText('Instructions to enable microphone access if problem persists')
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Start recording' })
  ).toHaveCount(0)
})
