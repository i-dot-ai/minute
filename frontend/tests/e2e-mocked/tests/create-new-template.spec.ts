import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect, type Page } from '@playwright/test'
import { uploadAudioFlow } from '@/tests/e2e-mocked/utilities/navigation'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(
  __dirname,
  '../../fixtures/sample-meeting.mp3'
)

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

const createNewTemplate = async (
  page: Page,
  templateType = 'Blank template'
) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Templates' }).click()

  await expect(page).toHaveURL(/\/templates$/)
  await page.getByRole('button', { name: 'Create new template' }).click()

  await page.getByRole('radio', { name: templateType }).check()
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/templates\/create/)
}

const checkNewTemplateInList = async (page: Page, templateName: string) => {
  await expect(page).toHaveURL(/\/templates$/)
  await expect(page.getByRole('link', { name: templateName })).toBeVisible()

  await uploadAudioFlow(page, sampleMeeting)

  const select = page.getByLabel('Choose a template:')
  await expect(select).toBeVisible()
  await expect(select.locator('option', { hasText: templateName })).toHaveCount(
    1
  )
}

test('create a SUMMARY template persists and is available when recording a new meeting', async ({
  page,
}) => {
  await createNewTemplate(page)

  await page
    .getByRole('textbox', { name: 'Template name' })
    .fill('E2E test template')
  await page
    .getByRole('textbox', { name: 'Description' })
    .fill('Template is for testing summaries')
  await page.getByRole('textbox', { name: 'Template content editor' }).click()
  await page.keyboard.type('This is a summary template for testing purposes')
  await page.getByRole('button', { name: 'Save template' }).click()

  await checkNewTemplateInList(page, 'E2E test template')
})

test('create a Q&A template persists and is available when recording a new meeting', async ({
  page,
}) => {
  await createNewTemplate(page)

  await page
    .getByRole('textbox', { name: 'Template name' })
    .fill('Q&A test template')
  await page
    .getByRole('textbox', { name: 'Description' })
    .fill('Template is for testing summaries')
  await page.getByRole('radio', { name: 'Q & A' }).check()
  await page
    .getByRole('textbox', { name: 'Style guide' })
    .fill('This is a style guide for testing purposes')
  await page.getByRole('button', { name: 'Add question' }).click()
  await page
    .getByRole('textbox', { name: 'Question text' })
    .fill('What is the purpose of this template?')
  await page
    .getByRole('textbox', { name: 'Question description' })
    .fill('It is to test the creation of a Q&A template')
  await page.getByRole('button', { name: 'Save template' }).click()

  await checkNewTemplateInList(page, 'Q&A test template')
})

test('create a template from an example and it is available when recording a new meeting', async ({
  page,
}) => {
  await createNewTemplate(page, 'My general')

  const templateName = page.getByRole('textbox', { name: 'Template name' })
  await expect(templateName).toHaveValue('My general')

  await templateName.fill('My general - updated for testing')

  await page.getByRole('button', { name: 'Save template' }).click()

  await checkNewTemplateInList(page, 'My general - updated for testing')
})
