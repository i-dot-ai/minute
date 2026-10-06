import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect, type Page } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

const editTemplate = async (page: Page, templateName: string) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Templates' }).click()
  await expect(page).toHaveURL(/\/templates$/)

  await page.getByRole('link', { name: templateName }).click()
  await expect(page).toHaveURL(/\/templates\/[0-9a-f-]+$/)

  await page.getByRole('button', { name: 'Edit' }).click()
}

const checkEditedTemplateInList = async (page: Page, templateName: string) => {
  await expect(page.getByText('Changes saved!')).toBeVisible()
  await expect(page).toHaveURL(/\/templates\/[0-9a-f-]+$/)

  await expect(page.getByRole('button', { name: 'Edit' })).toBeVisible()
  await expect(page.getByRole('heading', { name: templateName })).toBeVisible()

  await page.goto('/templates')
  await expect(
    page.getByRole('link', { name: new RegExp(templateName) })
  ).toBeVisible()
}

test('edit a SUMMARY template saves the changes', async ({ page }) => {
  await editTemplate(page, 'Project kickoff')

  const name = page.getByRole('textbox', { name: 'Template name' })
  await expect(name).toHaveValue('Project kickoff')
  await name.fill('Project kickoff - updated')

  await page
    .getByRole('textbox', { name: 'Description' })
    .fill('Updated description for testing edits')

  const editor = page.getByRole('textbox', { name: 'Template content editor' })
  await editor.click()
  await page.keyboard.press('ControlOrMeta+a')
  await page.keyboard.type('Updated template content')

  await page.getByRole('button', { name: 'Save' }).click()

  await checkEditedTemplateInList(page, 'Project kickoff - updated')
})

test('edit a Q&A template saves the changes', async ({ page }) => {
  await editTemplate(page, 'My Care')

  const name = page.getByRole('textbox', { name: 'Template name' })
  await expect(name).toHaveValue('My Care')
  await name.fill('My Care - updated')

  await page
    .getByRole('textbox', { name: 'Description' })
    .fill('Updated description for testing edits')

  await page
    .getByRole('textbox', { name: 'Style guide' })
    .fill('Updated style guide for testing purposes')

  await page.getByRole('button', { name: 'Add question' }).click()
  await page
    .getByRole('textbox', { name: 'Question text' })
    .fill('What is the purpose of this template?')
  await page
    .getByRole('textbox', { name: 'Question description' })
    .fill('It is to test editing a Q&A template')

  await page.getByRole('button', { name: 'Save' }).click()

  await checkEditedTemplateInList(page, 'My Care - updated')
})
