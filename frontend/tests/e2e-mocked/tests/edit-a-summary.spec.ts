import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import {
  goToSummaryPage,
  enterEditMode,
} from '@/tests/e2e-mocked/utilities/navigation'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

test('manually editing a summary persists the change', async ({ page }) => {
  await goToSummaryPage(page, meeting1.title!)
  await enterEditMode(page)

  const editor = page.getByRole('textbox', { name: 'Summary editor' })
  await editor.click()
  await page.keyboard.press('ControlOrMeta+End')
  await page.keyboard.type(' Edited summary marker')

  const savePost = page.waitForRequest(
    (req) =>
      req.method() === 'POST' && /\/minutes\/[^/]+\/versions$/.test(req.url())
  )
  await page.getByRole('button', { name: 'Save' }).click()

  const request = await savePost
  expect(request.postDataJSON()).toMatchObject({
    content_source: 'manual_edit',
    html_content: expect.stringContaining('Edited summary marker'),
  })

  await page.goto(new URL(page.url()).pathname)
  await expect(
    page.getByRole('textbox', { name: 'Summary editor' })
  ).toContainText('Edited summary marker')
})

test('renaming a transcription persists the new title', async ({ page }) => {
  await goToSummaryPage(page, meeting1.title!)
  await enterEditMode(page)

  const newTitle = 'Renamed meeting title'
  await page
    .getByRole('textbox', { name: 'Transcription title' })
    .fill(newTitle)

  const savePatch = page.waitForRequest(
    (req) =>
      req.method() === 'PATCH' && /\/transcriptions\/[^/]+$/.test(req.url())
  )
  await page.getByRole('button', { name: 'Save' }).click()

  const request = await savePatch
  expect(request.postDataJSON()).toMatchObject({ title: newTitle })

  await page.reload()
  await expect(
    page.getByRole('heading', { level: 1, name: newTitle })
  ).toBeVisible()
})

test('discarding an edit abandons the change', async ({ page }) => {
  await goToSummaryPage(page, meeting1.title!)
  await enterEditMode(page)

  let versionPosted = false
  page.on('request', (req) => {
    if (
      req.method() === 'POST' &&
      /\/minutes\/[^/]+\/versions$/.test(req.url())
    )
      versionPosted = true
  })

  const editor = page.getByRole('textbox', { name: 'Summary editor' })
  await editor.click()
  await page.keyboard.press('ControlOrMeta+End')
  await page.keyboard.type(' Discarded marker')

  await page.getByRole('button', { name: 'Discard' }).click()

  await expect(
    page.getByRole('button', { name: 'Edit', exact: true })
  ).toBeVisible()
  const summary = page.getByRole('textbox', { name: 'Summary editor' })
  await expect(summary).not.toContainText('Discarded marker')
  await expect(summary).toContainText("it's changed now and update twice")
  expect(versionPosted).toBe(false)
})

test('AI edit requests a new version with the instruction', async ({
  page,
}) => {
  await goToSummaryPage(page, meeting1.title!)
  await enterEditMode(page)

  await page.getByRole('button', { name: 'AI edit' }).click()

  const instruction = 'Make the tone more formal'
  await page.getByLabel('Edit instruction').fill(instruction)

  const aiPost = page.waitForRequest(
    (req) =>
      req.method() === 'POST' && /\/minutes\/[^/]+\/versions$/.test(req.url())
  )
  await page.getByRole('button', { name: 'Apply AI edit' }).click()

  const request = await aiPost
  expect(request.postDataJSON()).toMatchObject({
    content_source: 'ai_edit',
    ai_edit_instructions: { instruction },
  })
})
