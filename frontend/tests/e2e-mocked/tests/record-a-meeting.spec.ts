import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import {
  recordAudioFlow,
  statusToSummaryFlow,
} from '@/tests/e2e-mocked/utilities/navigation'
import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(
  __dirname,
  '../../fixtures/sample-meeting.mp3'
)

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

test('In person meeting to summary', async ({ page }) => {
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

test('Virtual meeting to summary', async ({ page }) => {
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

for (const language of ['en', 'cy']) {
  test(`Upload a file to summary (${language})`, async ({ page }) => {
    await page.goto('/')

    await page.getByRole('radio', { name: 'Upload a file' }).check()

    await page
      .locator('input[type="file"][name="file"]')
      .setInputFiles(sampleMeeting)

    await page.getByRole('button', { name: 'Upload file' }).click()
    const languageSelect = page.getByLabel('Choose a language')
    await expect(languageSelect).toHaveValue('en')
    for (const width of [1280, 375]) {
      await page.setViewportSize({ width, height: 720 })
      const pickers = await page.getByRole('dialog').evaluate((dialog) =>
        ['language', 'template'].map((id) => {
          const { width, height } = dialog
            .querySelector(`#${id}`)!
            .getBoundingClientRect()
          const label = dialog.querySelector(`label[for="${id}"]`)!
          return {
            width: Math.round(width),
            height: Math.round(height),
            labelHeight: Math.round(label.getBoundingClientRect().height),
            labelLineHeight: Math.round(
              parseFloat(getComputedStyle(label).lineHeight)
            ),
          }
        })
      )
      expect(pickers[0]).toEqual(pickers[1])
      expect(pickers[0].width).toBeLessThanOrEqual(224)
      expect(pickers[0].labelHeight).toBeLessThanOrEqual(
        pickers[0].labelLineHeight + 1
      )
    }
    await page.setViewportSize({ width: 1280, height: 720 })
    await languageSelect.selectOption(language)
    const transcriptionRequest = page.waitForRequest(
      (req) =>
        req.method() === 'POST' &&
        /\/api\/proxy\/transcriptions$/.test(req.url())
    )
    await page.getByRole('button', { name: 'Generate summary' }).click()
    expect((await transcriptionRequest).postDataJSON().language).toBe(language)

    await statusToSummaryFlow(page)
  })
}
