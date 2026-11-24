import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect } from '@playwright/test'

test('changing the display name updates the profile', async ({ page }) => {
  await mockBackend(page)

  await page.goto('/')
  await page
    .getByRole('button', { name: 'Name Surname open for profile links' })
    .click()
  await page.getByRole('link', { name: 'Your account' }).click()

  await expect(page).toHaveURL('/profile')
  await expect(page.getByRole('cell', { name: 'Name Surname' })).toBeVisible()

  await page.getByRole('button', { name: 'Change name' }).click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Change name' })
  ).toBeVisible()

  const nameInput = dialog.getByLabel('Change name')
  await expect(nameInput).toHaveValue('Name Surname')

  await nameInput.fill('New Name')
  await dialog.getByRole('button', { name: 'Save' }).click()

  await expect(dialog).toBeHidden()
  await expect(page.getByRole('cell', { name: 'New Name' })).toBeVisible()

  await page
    .getByRole('button', { name: 'New Name open for profile links' })
    .click()
  await expect(page.getByRole('heading', { name: 'New Name' })).toBeVisible()
})
