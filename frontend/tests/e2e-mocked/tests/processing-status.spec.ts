import { test, expect, type Page } from '@playwright/test'
import { GET } from '@/app/api/status/route'
import type {
  HourlyProcessingStatus,
  StatusBucket,
} from '@/lib/processing-status'
import { mockBackend } from '../utilities/mock-backend'

function bucket(start: string, values: Partial<StatusBucket> = {}) {
  return {
    start,
    completed: 0,
    failed: 0,
    failure_rate: null,
    avg_processing_seconds: null,
    audio_hours: 0,
    processing_seconds_per_audio_hour: null,
    per_audio_hour_seconds: {
      sample_count: 0,
      p50: null,
      p90: null,
      p99: null,
    },
    ...values,
  } satisfies StatusBucket
}

const hours = Array.from({ length: 24 }, (_, hour) =>
  bucket(`2026-11-02T${String(hour).padStart(2, '0')}:00:00Z`)
)
hours[1] = bucket('2026-11-02T01:00:00Z', {
  completed: 7,
  failed: 1,
  failure_rate: 0.125,
  per_audio_hour_seconds: { sample_count: 7, p50: 60, p90: 125, p99: 3661 },
})

const status: HourlyProcessingStatus = {
  partial: false,
  hours,
  last_10_minutes: bucket('2026-11-02T23:50:00Z', {
    completed: 20,
    failed: 1,
    failure_rate: 0.02,
    per_audio_hour_seconds: { sample_count: 20, p50: 45.4, p90: 90, p99: 120 },
  }),
}

async function openStatus(page: Page, body: HourlyProcessingStatus = status) {
  await page.route('**/api/status', (route) => route.fulfill({ json: body }))
  await page.goto('/status')
}

async function chartTable(page: Page, title: string) {
  const chart = page.locator('details').filter({ hasText: title })
  await chart.getByText('Show data').click()
  return chart.getByRole('table', { name: title })
}

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

test('shows the last 10 minutes', async ({ page }) => {
  await openStatus(page)
  await expect(
    page.getByRole('heading', { name: 'Last 10 mins', exact: true })
  ).toBeVisible()
  const card = (name: string) =>
    page.locator('.analytics-card').filter({ hasText: name })
  await expect(card('Processing time per audio hour:')).toContainText('45s')
  await expect(card('Error rate:')).toContainText('2.00%')
  await expect(card('Transcriptions completed:')).toContainText('20')
  await expect(page.getByRole('status')).toHaveCount(0)
})

test('warns about incomplete timings without hiding counts or error rates', async ({
  page,
}) => {
  await openStatus(page, { ...status, partial: true })
  await expect(page.getByRole('status')).toContainText(
    'Processing times are based on incomplete data'
  )
  await expect(page.getByRole('status')).toContainText(
    'Transcription counts and error rates are not affected by this limit.'
  )
  await expect(
    page.locator('.analytics-card').filter({ hasText: 'Error rate:' })
  ).toContainText('2.00%')
  await expect(
    page
      .locator('.analytics-card')
      .filter({ hasText: 'Transcriptions completed:' })
  ).toContainText('20')
  const completed = await chartTable(page, 'Transcriptions completed per hour')
  await expect(
    completed.getByRole('row').filter({ hasText: '01:00' })
  ).toHaveText(/01:00\s*7/)
  const errors = await chartTable(page, 'Error rate per hour')
  await expect(errors.getByRole('row').filter({ hasText: '01:00' })).toHaveText(
    /01:00\s*12\.5%/
  )
})

test('charts the last 24 hours with a data table for each', async ({
  page,
}) => {
  await openStatus(page)
  for (const name of [
    'Processing time per audio hour',
    'Transcriptions completed per hour',
    'Error rate per hour',
  ]) {
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    await expect(page.getByRole('img', { name, exact: true })).toBeVisible()
  }

  const processing = await chartTable(page, 'Processing time per audio hour')
  await expect(processing.getByRole('row')).toHaveCount(25)
  await expect(
    processing.getByRole('row').filter({ hasText: '01:00' })
  ).toHaveText(/01:00\s*1m 0s\s*2m 5s\s*1h 1m 1s/)
  await expect(
    processing.getByRole('row').filter({ hasText: '00:00' })
  ).toHaveText(/00:00\s*–\s*–\s*–/)

  const completed = await chartTable(page, 'Transcriptions completed per hour')
  await expect(
    completed.getByRole('row').filter({ hasText: '01:00' })
  ).toHaveText(/01:00\s*7/)

  const errors = await chartTable(page, 'Error rate per hour')
  await expect(errors.getByRole('row').filter({ hasText: '01:00' })).toHaveText(
    /01:00\s*12\.5%/
  )
  await expect(errors.getByRole('row').filter({ hasText: '00:00' })).toHaveText(
    /00:00\s*–/
  )
})

test('shows N/A error rate and UK hour labels', async ({ page }) => {
  await openStatus(page, {
    ...status,
    hours: [bucket('2026-07-01T09:00:00Z', { completed: 3 })],
    last_10_minutes: bucket('2026-07-01T09:50:00Z'),
  })
  await expect(
    page.locator('.analytics-card').filter({ hasText: 'Error rate:' })
  ).toContainText('N/A')
  const completed = await chartTable(page, 'Transcriptions completed per hour')
  await expect(completed.getByRole('row').nth(1)).toHaveText(/^10:00\s*3$/)
})

test('unavailable status shows a message instead of metrics', async ({
  page,
}) => {
  await page.route('**/api/status', (route) => route.fulfill({ status: 503 }))
  await page.goto('/status')
  await expect(
    page.getByText('Metrics are temporarily unavailable.')
  ).toBeVisible()
  await expect(page.locator('.analytics-card')).toHaveCount(0)
  await expect(page.locator('canvas')).toHaveCount(0)
})

test('server cache shares one snapshot across users for one minute', async () => {
  const originalFetch = global.fetch
  const originalNow = Date.now
  const originalHost = process.env.BACKEND_HOST
  let now = 0
  let calls = 0
  const firstUser = new Request('http://localhost/api/status', {
    headers: { 'x-amzn-oidc-data': 'first-user' },
  })
  const secondUser = new Request('http://localhost/api/status', {
    headers: { 'x-amzn-oidc-data': 'second-user' },
  })
  try {
    process.env.BACKEND_HOST = 'http://backend:8080'
    Date.now = () => now
    global.fetch = async (url, options) => {
      expect(url).toBe('http://backend:8080/status/hourly')
      expect(options?.cache).toBe('no-store')
      calls += 1
      return Response.json(status)
    }
    const responses = await Promise.all([GET(firstUser), GET(secondUser)])
    expect(await responses[0].json()).toEqual(await responses[1].json())
    expect(calls).toBe(1)
    now = 59_999
    expect((await GET(secondUser)).status).toBe(200)
    expect(calls).toBe(1)
    now = 60_000
    expect((await GET(secondUser)).status).toBe(200)
    expect(calls).toBe(2)
  } finally {
    global.fetch = originalFetch
    Date.now = originalNow
    if (originalHost === undefined) delete process.env.BACKEND_HOST
    else process.env.BACKEND_HOST = originalHost
  }
})
