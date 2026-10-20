import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(__dirname, '../fixtures/sample-meeting.mp3')

test('Upload an audio file and process summary and transcript', async ({
  page,
}) => {
  test.setTimeout(10 * 60_000)
  await page.goto('/')

  await page.getByRole('radio', { name: 'Upload a file' }).check()

  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)

  await page.getByRole('button', { name: 'Upload file' }).click()
  await page.getByRole('button', { name: 'Generate summary' }).click()

  await expect(page).toHaveURL(/\/new\/status\/[^/]+$/, { timeout: 30_000 })

  await expect(page.getByText(/Transcribing|Generating summary/)).toBeVisible()

  // Wait for a TERMINAL state. .or() resolves as soon as either appears,
  // so a failure doesn't burn the full timeout.
  const ready = page.getByRole('heading', { name: 'Ready' })
  const failed = page.getByRole('heading', { name: 'Failed to process' })
  await expect(ready.or(failed)).toBeVisible({ timeout: 8 * 60_000 })
  await expect(ready).toBeVisible({ timeout: 10_000 })

  await page.getByRole('link', { name: 'View transcription' }).click()
  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary\/[^/]+$/, {
    timeout: 30_000,
  })

  // loose check that at least one key word from the meeting is in summary and transcript
  const summaryContent = page.locator('#tour-summary')
  await expect(summaryContent).toBeVisible()
  await expect(summaryContent).toContainText(
    /absenteeism|student|attendance|support/i
  )

  await page.getByRole('link', { name: 'Transcript', exact: true }).click()
  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/transcript/, {
    timeout: 30_000,
  })
  await expect(page.getByRole('main')).toContainText(/absent|student|success/i)
})
