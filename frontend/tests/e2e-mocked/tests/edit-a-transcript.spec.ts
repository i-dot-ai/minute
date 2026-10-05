import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import {
  goToTranscriptPage,
  enterEditMode,
} from '@/tests/e2e-mocked/utilities/navigation'
import {
  waitForTranscriptPatch,
  waitForSummaryRegenerate,
} from '@/tests/e2e-mocked/utilities/routes/transcription'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

test('editing a transcript entry persists the change', async ({ page }) => {
  await goToTranscriptPage(page, meeting1.title!)
  await enterEditMode(page)

  const newText = 'Edited transcript entry text'
  await page.getByLabel('Transcript text for entry 1').fill(newText)

  const savePatch = waitForTranscriptPatch(page)
  await page.getByRole('button', { name: 'Save' }).click()

  const patchRequest = await savePatch
  const body = patchRequest.postDataJSON() as {
    dialogue_entries: Array<{ text: string }>
  }
  expect(body.dialogue_entries[0].text).toBe(newText)

  await expect(page.getByText(newText)).toBeVisible()
})

test('renaming all speakers persists and regenerates the summary', async ({
  page,
}) => {
  await goToTranscriptPage(page, meeting1.title!)
  await enterEditMode(page)

  await page.getByRole('button', { name: 'Edit speaker names' }).click()

  const renames = ['Alice', 'Bob', 'Carol', 'Dan', 'Erin']
  for (const [index, name] of renames.entries()) {
    await page.getByLabel(`Speaker ${index + 1}`).fill(name)
  }

  const savePatch = waitForTranscriptPatch(page)
  const regeneratePost = waitForSummaryRegenerate(page)
  await page
    .getByRole('button', { name: 'Save and create new summary' })
    .click()

  const patchRequest = await savePatch
  const body = patchRequest.postDataJSON() as {
    dialogue_entries: Array<{ speaker: string }>
  }
  const speakers = new Set(body.dialogue_entries.map((entry) => entry.speaker))
  expect(speakers).toEqual(new Set(renames))

  await regeneratePost

  await expect(page.getByText('New summary is being generated')).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Alice' }).first()
  ).toBeVisible()
})
