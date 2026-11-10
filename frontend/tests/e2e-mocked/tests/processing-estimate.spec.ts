import { test, expect } from '@playwright/test'
import type { HourlyProcessingStatus } from '@/lib/processing-status'
import { meeting1 } from '../mocked-responses/mock-meeting-1'
import { mockBackend } from '../utilities/mock-backend'

const statusWithP50: HourlyProcessingStatus = {
  partial: false,
  hours: [],
  last_10_minutes: {
    start: '2026-11-02T23:50:00Z',
    completed: 4,
    failed: 0,
    failure_rate: 0,
    avg_processing_seconds: 360,
    audio_hours: 4,
    processing_seconds_per_audio_hour: 360,
    per_audio_hour_seconds: {
      sample_count: 4,
      p50: 360,
      p90: 360,
      p99: 360,
    },
  },
}

test.beforeEach(async ({ page }) => {
  await mockBackend(page, 'meeting-1', 'in_progress')
  // Start the clock a second after the fixture transcription was created, so
  // the countdown stays a whisker below its estimate for the whole test.
  await page.clock.install({
    time: new Date(new Date(meeting1.created_datetime).getTime() + 1_000),
  })
  // An hour of audio: the constants give 2 minutes of processing, while a
  // p50 of 360s per audio hour gives 6.
  await page.addInitScript(
    ([key, value]) => {
      sessionStorage.setItem(key, value)
    },
    [`recording-duration-sec:${meeting1.id}`, '3600']
  )
})

test('shows the constant estimate first, then updates from the live p50', async ({
  page,
}) => {
  let release!: () => void
  const pending = new Promise<void>((resolve) => {
    release = resolve
  })
  await page.route('**/api/status', async (route) => {
    await pending
    await route.fulfill({ json: statusWithP50 })
  })

  await page.goto(`/new/status/${meeting1.id}`)
  const estimate = page.locator('p').filter({ hasText: 'Estimated time left' })
  await expect(estimate).toContainText('2 minutes')

  release()
  await expect(estimate).toContainText('6 minutes')
})

test('keeps the constant estimate when the status has no recent data', async ({
  page,
}) => {
  await page.goto(`/new/status/${meeting1.id}`)
  await expect(
    page.locator('p').filter({ hasText: 'Estimated time left' })
  ).toContainText('2 minutes')
})
