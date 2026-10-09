import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { userTemplates } from '@/tests/e2e-mocked/mocked-responses/user-templates'
import { test, expect } from '@playwright/test'

test('deleting a template removes it from the list', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')
  await page.getByRole('link', { name: 'Templates' }).click()
  await expect(page).toHaveURL(/\/templates$/)

  const target = userTemplates[0]
  const other = userTemplates[1]
  const row = page.getByRole('link', { name: new RegExp(target.name) })
  await expect(row).toBeVisible()

  const deleteRequest = page.waitForRequest(
    (req) =>
      req.method() === 'DELETE' &&
      new RegExp(`/user-templates/${target.id}$`).test(req.url())
  )

  await page.getByRole('button', { name: `Delete ${target.name}` }).click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText(target.name)).toBeVisible()
  await dialog.getByRole('button', { name: 'Delete' }).click()

  await deleteRequest

  await expect(
    page.getByRole('link', { name: new RegExp(target.name) })
  ).toHaveCount(0)
  await expect(
    page.getByRole('link', { name: new RegExp(other.name) })
  ).toBeVisible()
})

test('cancelling the delete dialog keeps the template', async ({ page }) => {
  await mockBackend(page)
  await page.goto('/')
  await page.getByRole('link', { name: 'Templates' }).click()
  await expect(page).toHaveURL(/\/templates$/)
  
  const target = userTemplates[0]
  let deleteFired = false
  page.on('request', (req) => {
    if (req.method() === 'DELETE' && /\/user-templates\/[^/]+$/.test(req.url()))
      deleteFired = true
  })

  await page.getByRole('button', { name: `Delete ${target.name}` }).click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Cancel' }).click()

  await expect(dialog).toBeHidden()
  await expect(
    page.getByRole('link', { name: new RegExp(target.name) })
  ).toBeVisible()
  expect(deleteFired).toBe(false)
})
