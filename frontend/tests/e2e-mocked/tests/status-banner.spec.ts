import { test, expect, type Page } from '@playwright/test'
import type {
  HourlyProcessingStatus,
  StatusBucket,
} from '@/lib/processing-status'
import { processingAlert } from '@/lib/processing-status'

import { mockBackend } from '../utilities/mock-backend'

function bucket(start: string, values: Partial<StatusBucket> = {}) {
  return {
    start,
    completed: 0,
    failed: 0,
    failure_rate: null,
    avg_processing_seconds: null,
    audio_hours: 0,
    projected_one_hour_seconds: null,
    ...values,
  } satisfies StatusBucket
}

const last10 = (values: Partial<StatusBucket> = {}) => {
  const body: HourlyProcessingStatus = {
    collected_at: '2026-11-02T23:50:00Z',
    partial: false,
    hours: Array.from({ length: 24 }, (_, hour) =>
      bucket(`2026-11-02T${String(hour).padStart(2, '0')}:00:00Z`)
    ),
    last_10_minutes: bucket('2026-11-02T23:50:00Z', {
      completed: 20,
      failed: 1,
      failure_rate: 0.02,
      projected_one_hour_seconds: 45.4,
      ...values,
    }),
  }
  return body
}

const status = last10()

// Copy lives in processingAlert; asserting against it keeps these tests copy-agnostic.
const bannerText = (values?: Partial<StatusBucket>) =>
  processingAlert(last10(values).last_10_minutes).message

async function openHome(page: Page, body: HourlyProcessingStatus = status) {
  await page.route('**/api/status', (route) => route.fulfill({ json: body }))
  await page.goto('/')
}

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

// The message the banner shows for a definite failure surge; healthy/quiet
// fixtures must never display it.
const problemMessage = bannerText({
  completed: 10,
  failed: 10,
  failure_rate: 0.6,
})

test('hides the service banner while the service is healthy', async ({
  page,
}) => {
  await openHome(page)
  await expect(page.getByText(problemMessage)).toHaveCount(0)
})

test('alerts on a high error rate once enough runs have failed', async ({
  page,
}) => {
  const failing = { completed: 10, failed: 10, failure_rate: 0.6 }
  await openHome(page, last10(failing))
  await expect(page.getByText(bannerText(failing))).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'system status page' })
  ).toBeVisible()
})

test('alerts once 3 meetings have failed even in a tiny window', async ({
  page,
}) => {
  const tiny = { completed: 1, failed: 3, failure_rate: 0.75 }
  await openHome(page, last10(tiny))
  await expect(page.getByText(bannerText(tiny))).toBeVisible()
})

test('keeps the banner quiet when too few meetings finish, even at 100%', async ({
  page,
}) => {
  await openHome(page, last10({ completed: 1, failed: 2, failure_rate: 0.67 }))
  await expect(page.getByText(problemMessage)).toHaveCount(0)
})

test('alerts on long processing times', async ({ page }) => {
  const slow = {
    completed: 20,
    failed: 1,
    failure_rate: 0.02,
    projected_one_hour_seconds: 700,
  }
  await openHome(page, last10(slow))
  await expect(page.getByText(bannerText(slow))).toBeVisible()
})

test('reports both problems together in one banner', async ({ page }) => {
  const both = {
    completed: 10,
    failed: 10,
    failure_rate: 0.6,
    projected_one_hour_seconds: 700,
  }
  await openHome(page, last10(both))
  await expect(page.getByText(bannerText(both))).toBeVisible()
})
