import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { userTemplates } from '@/tests/e2e-mocked/mocked-responses/user-templates'
import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(__dirname, '../../fixtures/sample-meeting.mp3')

const template = userTemplates.find((t) => t.name === 'Project kickoff')!

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

test('setting a default template applies it in the upload flow', async ({
  page,
}) => {
  await page.goto('/templates')
  await page.getByRole('link', { name: new RegExp(template.name!) }).click()

  await expect(page).toHaveURL(new RegExp(`/templates/${template.id}$`))
  await page.getByRole('button', { name: 'Set as default' }).click()
  await expect(
    page.getByRole('button', { name: 'Remove default' })
  ).toBeVisible()

  await page.goto('/')
  await page.getByRole('radio', { name: 'Upload a file' }).check()
  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)
  await page.getByRole('button', { name: 'Upload file' }).click()

  const select = page.getByLabel('Choose a template:')
  await expect(select).toBeVisible()
  await expect(
    select.locator('option', { hasText: `${template.name} (Default)` })
  ).toHaveCount(1)
})
