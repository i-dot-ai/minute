import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect } from '@playwright/test'

test('changing the display name updates the profile', async ({ page }) => {
  await mockBackend(page)

  await page.goto('/')
  await page.getByRole('button', { name: 'Name Surname' }).click()
  await page.getByRole('button', { name: 'Change name' }).click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Change name' })
  ).toBeVisible()

  const nameInput = dialog.getByLabel('Display name')
  await expect(nameInput).toHaveValue('Name Surname')

  await nameInput.fill('New Name')
  await dialog.getByRole('button', { name: 'Save' }).click()

  await expect(dialog).toBeHidden()
  await expect(page.getByRole('button', { name: 'New Name' })).toBeVisible()

  await page.locator('#profile-button').click()
  await expect(page.getByRole('heading', { name: 'New Name' })).toBeVisible()
})
