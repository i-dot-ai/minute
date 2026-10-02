import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(__dirname, '../../fixtures/sample-meeting.mp3')

const recordAudioFlow = async (page: Page) => {
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

const statusToSummaryFlow = async (page: Page) => {
  await expect(page).toHaveURL(/\/new\/status\/[^/]+$/, { timeout: 30_000 })
  await expect(page.getByRole('heading', { name: 'Ready' })).toBeVisible()

  await page.getByRole('link', { name: 'View transcription' }).click()

  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary\/[^/]+$/, {
    timeout: 30_000,
  })
  await expect(
    page.getByRole('heading', { level: 1, name: meeting1.title! })
  ).toBeVisible()
}

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
  // getDisplayMedia isn't covered by the fake-media flags and may reject in CI.
  await page.addInitScript(() => {
    navigator.mediaDevices.getDisplayMedia = async () => {
      ;(
        window as unknown as { __getDisplayMediaCalled?: boolean }
      ).__getDisplayMediaCalled = true
      return navigator.mediaDevices.getUserMedia({ audio: true })
    }
  })
})

test('In person meeting to summary', async ({ page, browserName }) => {
  test.skip(
    browserName !== 'chromium',
    'Mic/screen capture relies on Chromium fake-media-device flags'
  )
  await page.goto('/')
  await page.getByRole('radio', { name: 'In person' }).check()

  await expect(page.getByLabel('Select microphone:')).toBeEnabled()
  await expect(
    page.getByRole('option', { name: 'Requesting microphone access...' })
  ).toHaveCount(0)

  await page.getByRole('button', { name: 'Start recording' }).click()

  await recordAudioFlow(page)
  await statusToSummaryFlow(page)
})

test('Virtual meeting to summary', async ({ page, browserName }) => {
  test.skip(
    browserName !== 'chromium',
    'Mic/screen capture relies on Chromium fake-media-device flags'
  )
  await page.goto('/')
  await page.getByRole('radio', { name: 'Virtual meeting' }).check()

  await expect(
    page.getByRole('heading', { name: 'Before you start' })
  ).toBeVisible()

  await expect(page.getByLabel('Select microphone:')).toBeEnabled()
  await expect(
    page.getByRole('option', { name: 'Requesting microphone access...' })
  ).toHaveCount(0)

  await page.getByRole('button', { name: 'Start recording' }).click()

  // check that screen capture was requested, since getDisplayMedia is stubbed to always succeed
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as unknown as { __getDisplayMediaCalled?: boolean })
            .__getDisplayMediaCalled === true
      )
    )
    .toBe(true)

  await recordAudioFlow(page)
  await statusToSummaryFlow(page)
})

test('Upload a file to summary', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('radio', { name: 'Upload a file' }).check()

  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)

  await page.getByRole('button', { name: 'Upload file' }).click()
  await page.getByRole('button', { name: 'Generate summary' }).click()

  await statusToSummaryFlow(page)
})
