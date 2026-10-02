import { expect, type Page } from '@playwright/test'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'

export const goToSummaryPage = async (page: Page, meetingTitle: string) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'transcripts' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  await page.getByRole('link', { name: meetingTitle }).first().click()

  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary\/[^/]+$/)
  await expect(
    page.getByRole('heading', { level: 1, name: meetingTitle })
  ).toBeVisible()
}

export const enterEditMode = async (page: Page) => {
  await page.getByRole('button', { name: 'Edit', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
}

export const goToTranscriptPage = async (page: Page, meetingTitle: string) => {
  await goToSummaryPage(page, meetingTitle)
  await page.getByRole('link', { name: 'Transcript', exact: true }).click()
  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/transcript$/)
}

export const recordAudioFlow = async (page: Page) => {
  await expect(page).toHaveURL('/new')
  await expect(
    page.getByRole('heading', { name: 'Recording', exact: true })
  ).toBeVisible()

  // Let a MediaRecorder chunk (emitted every 1s) land so there's audio to save.
  await page.waitForTimeout(1500)

  await page
    .getByRole('button', { name: 'Stop recording and save' })
    .first()
    .click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Stop recording and save' }).click()
}

export const statusToSummaryFlow = async (page: Page) => {
  await expect(page).toHaveURL(/\/new\/status\/[^/]+$/, { timeout: 10_000 })
  await expect(page.getByRole('heading', { name: 'Ready' })).toBeVisible()

  await page.getByRole('link', { name: 'View transcription' }).click()

  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary\/[^/]+$/, {
    timeout: 10_000,
  })
  await expect(
    page.getByRole('heading', { level: 1, name: meeting1.title! })
  ).toBeVisible()
}
