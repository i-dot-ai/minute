import { expect, test, type Page } from '@playwright/test'
import type {
  PaginatedTranscriptionSearchResponse,
  TranscriptionSearchMatch,
} from '@/lib/client'
import { redactSearchTelemetry, redactSearchUrl } from '@/lib/search-privacy'
import { mockBackend } from '../utilities/mock-backend'
import { json } from '../utilities/routes/general'
import { transcriptions } from '../mocked-responses/transcriptions'
import { meeting1Minutes } from '../mocked-responses/mock-meeting-1.minutes'
import { meeting1Versions } from '../mocked-responses/mock-meeting-1.versions'

const meetingTitle = 'Weekly Student Success Meeting'
const meeting = transcriptions.items[0]

// Keyed on the search term (lowercased): which source the match comes from.
const MATCHES: Record<string, TranscriptionSearchMatch[]> = {
  'student success': [
    {
      source: 'title',
      snippet: 'Student Success',
      snippet_start: 7,
      highlights: [{ start: 0, end: 15 }],
    },
  ],
  'speaker 3': [
    {
      source: 'speaker',
      snippet: 'Speaker 3',
      snippet_start: 0,
      highlights: [{ start: 0, end: 9 }],
      entry_index: 3,
      speaker: 'Speaker 3',
      start_time: 30.27,
      end_time: 44.43,
    },
  ],
  'pancake breakfast': [
    {
      source: 'transcript',
      snippet: 'like a pancake breakfast to encourage',
      snippet_start: 100,
      highlights: [{ start: 7, end: 24 }],
      entry_index: 1,
      speaker: 'Speaker 2',
    },
  ],
  absenteeism: [
    {
      source: 'summary',
      snippet: 'rising trend in student Friday absenteeism',
      snippet_start: 0,
      highlights: [{ start: 31, end: 42 }],
      minute_id: meeting1Minutes[0].id,
      minute_version_id: meeting1Versions[0].id,
    },
  ],
}

test('search terms are redacted from frontend telemetry', () => {
  for (const [url, expected] of [
    [
      'https://minute.test/transcriptions?q=private&page=2&filterBy=failed',
      'https://minute.test/transcriptions?page=2&filterBy=failed',
    ],
    ['/transcriptions?q=private', '/transcriptions'],
    ['/transcriptions?page=2', '/transcriptions?page=2'],
    [
      '/api/proxy/transcriptions/search?search=private',
      '/api/proxy/transcriptions/search',
    ],
    ['/search?keywords=private', '/search'],
    [
      '/transcriptions/123/transcript#search-match?text=private',
      '/transcriptions/123/transcript',
    ],
    ['http://', 'http://'],
  ]) {
    expect(redactSearchUrl(url)).toBe(expected)
  }
  const telemetry = redactSearchTelemetry({
    request: {
      url: 'https://minute.test/transcriptions?q=private',
      query_string: 'q=private',
      headers: { Referer: 'https://minute.test/transcriptions?q=private' },
    },
    breadcrumbs: [
      { data: { to: '/transcriptions?q=private' } },
      { data: { url: '/api/proxy/transcriptions/search?search=private' } },
    ],
    spans: [
      {
        span_id: '0123456789abcdef',
        trace_id: '0123456789abcdef0123456789abcdef',
        start_timestamp: 0,
        data: { 'http.url': '/transcriptions?q=private' },
      },
    ],
  })
  expect(JSON.stringify(telemetry)).not.toContain('private')
})

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
  await page.route('**/api/proxy/transcriptions/search?**', (route) => {
    const term = (
      new URL(route.request().url()).searchParams.get('search') ?? ''
    )
      .trim()
      .toLowerCase()
    const matches = MATCHES[term] ?? []
    const response: PaginatedTranscriptionSearchResponse = {
      items: matches.length
        ? [{ ...meeting, matches, matches_truncated: false }]
        : [],
      total_count: matches.length ? 1 : 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
    }
    return route.fulfill(json(200, response))
  })
})

async function searchFor(page: Page, term: string) {
  const searchBox = page.getByRole('searchbox', {
    name: 'Search transcriptions',
  })
  await searchBox.fill(term)
  await searchBox.press('Enter')
}

test('a search term in the title finds the meeting', async ({ page }) => {
  await page.goto('/transcriptions')
  await searchFor(page, 'Student Success')

  const row = page.getByRole('row', { name: meetingTitle })
  await expect(row).toBeVisible()
  await expect(row.locator('strong')).toHaveText('Student Success')
})

test('a search term in the speaker finds the meeting', async ({ page }) => {
  await page.goto('/transcriptions')
  await searchFor(page, 'Speaker 3')

  const row = page.getByRole('row', { name: meetingTitle })
  await expect(row).toBeVisible()
  await expect(row.locator('strong')).toHaveText('Speaker 3')
})

test('a search term in the transcript finds the meeting', async ({ page }) => {
  await page.goto('/transcriptions')
  await searchFor(page, 'pancake breakfast')

  const row = page.getByRole('row', { name: meetingTitle })
  await expect(row).toBeVisible()
  await expect(row.locator('strong')).toHaveText('pancake breakfast')
})

test('a search term in the summary finds the meeting', async ({ page }) => {
  await page.goto('/transcriptions')
  await searchFor(page, 'absenteeism')

  const row = page.getByRole('row', { name: meetingTitle })
  await expect(row).toBeVisible()
  await expect(row.locator('strong')).toHaveText('absenteeism')
})

test('a search with no matches shows the no results message', async ({
  page,
}) => {
  await page.goto('/transcriptions')
  await searchFor(page, 'giraffe')

  await expect(
    page.getByText('No transcriptions found for giraffe')
  ).toBeVisible()
  await expect(page.getByRole('row', { name: meetingTitle })).toHaveCount(0)
})
