import { test, expect } from '@playwright/test'
import { GET } from '@/app/api/status/route'
import { mockBackend } from '../utilities/mock-backend'

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

for (const { rate, colour, message } of [
  {
    rate: null,
    colour: 'text-green-700',
    message:
      'We’re fully operational. We’re not aware of any issues affecting our systems.',
  },
  {
    rate: 0.000099,
    colour: 'text-green-700',
    message: 'We’re fully operational.',
  },
  {
    rate: 0.0001,
    colour: 'text-yellow-600',
    message: "Degraded performance. We're aware of users experiencing errors.",
  },
  {
    rate: 0.04999,
    colour: 'text-yellow-600',
    message: 'Degraded performance.',
  },
  {
    rate: 0.05,
    colour: 'text-red-700',
    message:
      "Partial outage. We're aware of users experiencing elevated errors.",
  },
]) {
  test(`processing panel shows ${colour} at failure rate ${rate}`, async ({
    page,
  }) => {
    await page.route('**/api/status', (route) =>
      route.fulfill({
        json: {
          horizon_seconds: 600,
          components: {
            transcription: {
              counts: { completed: 0 },
              failure_rate: rate,
              processing_time_seconds: { p50: null, p90: null, p99: null },
            },
          },
        },
      })
    )
    await page.goto('/')
    const panel = page.getByRole('region', { name: 'Status', exact: true })
    await expect(
      panel.getByRole('heading', { name: 'Status', exact: true })
    ).toHaveCount(0)
    await expect(panel.locator(`svg.${colour}`)).toBeVisible()
    await expect(panel).toContainText(message)
    await expect(panel).not.toContainText('In the last')
  })
}

test('unavailable status does not claim the service is operational', async ({
  page,
}) => {
  await page.route('**/api/status', (route) => route.fulfill({ status: 503 }))
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Status', exact: true })
  await expect(panel).toContainText('Status is temporarily unavailable.')
  await expect(panel.locator('svg')).toHaveCount(0)
  await expect(
    page.getByRole('heading', { name: 'Record a meeting', exact: true })
  ).toBeVisible()
})

for (const { alert, colour, headline } of [
  {
    alert: 'yellow',
    colour: 'text-yellow-600',
    headline: 'Degraded performance.',
  },
  { alert: 'red', colour: 'text-red-700', headline: 'Partial outage.' },
]) {
  test(`alert=${alert} previews status without requesting or changing cached metrics`, async ({
    page,
  }) => {
    let requests = 0
    await page.route('**/api/status', (route) => {
      requests += 1
      return route.fulfill({ status: 503 })
    })
    await page.goto(`/?alert=${alert}`)
    const panel = page.getByRole('region', { name: 'Status', exact: true })
    await expect(panel.locator(`svg.${colour}`)).toBeVisible()
    await expect(panel.locator('strong')).toHaveText(headline)
    expect(requests).toBe(0)

    await page.goto('/?alert=invalid')
    await expect(panel).toContainText('Status is temporarily unavailable.')
    expect(requests).toBe(1)
  })
}

test('metrics expand and collapse without refetching status', async ({
  page,
}) => {
  let requests = 0
  await page.route('**/api/status', (route) => {
    requests += 1
    return route.fulfill({
      json: {
        horizon_seconds: 600,
        components: {
          transcription: {
            counts: { completed: 20 },
            failure_rate: 0.02,
            processing_time_seconds: { p50: 45.4, p90: 120.5, p99: 3661 },
          },
        },
      },
    })
  })
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Status', exact: true })
  await expect(panel).toContainText('Degraded performance.')
  const toggle = panel.getByRole('button', { name: 'Show metrics' })
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await expect(panel.getByRole('separator')).toBeHidden()
  await expect(panel.getByText('Last 10 minutes:')).toBeHidden()
  await toggle.click()
  await expect(
    panel.getByRole('button', { name: 'Hide metrics' })
  ).toHaveAttribute('aria-expanded', 'true')
  await expect(panel.getByRole('separator')).toBeVisible()
  for (const text of [
    'Last 10 minutes:',
    'Transcriptions: 20',
    'Error rate: 2.00%',
    'Processing time (P50): 45s',
    'Processing time (P90): 2m 1s',
    'Processing time (P99): 1h 1m 1s',
  ]) {
    await expect(panel.getByText(text, { exact: true })).toBeVisible()
  }
  await panel.getByRole('button', { name: 'Hide metrics' }).click()
  await expect(panel.getByText('Last 10 minutes:')).toBeHidden()
  await expect(panel.getByRole('separator')).toBeHidden()
  expect(requests).toBe(1)
})

for (const { alert, errorRate, headline } of [
  { alert: 'yellow', errorRate: '3.12%', headline: 'Degraded performance.' },
  { alert: 'red', errorRate: '20.26%', headline: 'Partial outage.' },
]) {
  test(`alert=${alert} overrides error rate while preserving real counts and timings`, async ({
    page,
  }) => {
    await page.route('**/api/status', (route) =>
      route.fulfill({
        json: {
          horizon_seconds: 86_400,
          components: {
            transcription: {
              counts: { completed: 0 },
              failure_rate: null,
              processing_time_seconds: { p50: null, p90: null, p99: null },
            },
          },
        },
      })
    )
    await page.goto(`/?alert=${alert}`)
    const panel = page.getByRole('region', { name: 'Status', exact: true })
    await panel.getByRole('button', { name: 'Show metrics' }).click()
    await expect(panel.getByText('Last 1 day:')).toBeVisible()
    await expect(
      panel.getByText('Transcriptions: 0', { exact: true })
    ).toBeVisible()
    await expect(
      panel.getByText(`Error rate: ${errorRate}`, { exact: true })
    ).toBeVisible()
    await expect(panel.getByText(/Processing time \(P\d+\): N\/A/)).toHaveCount(
      3
    )
    await expect(panel.locator('strong')).toHaveText(headline)
  })
}

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
      expect(url).toBe('http://backend:8080/status?horizon=10m')
      expect(options?.cache).toBe('no-store')
      calls += 1
      return Response.json({ horizon_seconds: 600, components: {} })
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
