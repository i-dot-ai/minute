import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import type { PaginatedTranscriptionSearchResponse } from '@/lib/client'
import { redactSearchTelemetry, redactSearchUrl } from '@/lib/search-privacy'
import { mockBackend } from '../utilities/mock-backend'
import { json } from '../utilities/routes/general'
import { meeting1 } from '../mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '../mocked-responses/mock-meeting-1.minutes'
import { meeting1Versions } from '../mocked-responses/mock-meeting-1.versions'

const snippet = '😀 The budget needs approval & agreement.'
const highlights = [
  { start: 7, end: 13 },
  { start: 20, end: 28 },
]
const paragraphs = Array.from(
  { length: 35 },
  (_, index) => `<p>Earlier discussion ${index}: nothing relevant here.</p>`
).join('')

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
  await page.route(`**/api/proxy/transcriptions/${meeting1.id}`, (route) =>
    route.fulfill(
      json(200, {
        ...meeting1,
        dialogue_entries: Array.from({ length: 35 }, (_, index) => ({
          speaker: index === 30 ? 'Alex Jones' : 'Other speaker',
          text:
            index === 30
              ? snippet
              : `Earlier discussion ${index}: nothing relevant here.`,
          start_time: index * 10,
          end_time: index * 10 + 9,
        })),
      })
    )
  )
  await page.route(
    `**/api/proxy/minutes/${meeting1Minutes[0].id}/versions`,
    (route) =>
      route.fulfill(
        json(200, [
          {
            ...meeting1Versions[0],
            html_content:
              '<p>The newest version does not contain the match.</p>',
          },
          {
            ...meeting1Versions[1],
            html_content:
              paragraphs +
              '<p>😀 The bud<strong>get</strong> needs approval &amp; agreement.</p>' +
              paragraphs,
          },
        ])
      )
  )
  await page.route('**/api/proxy/transcriptions/search?**', (route) => {
    const params = new URL(route.request().url()).searchParams
    const query = params.get('search')
    if (query === 'error') return route.fulfill(json(500, {}))
    const currentPage = Number(params.get('page') ?? 1)
    const response: PaginatedTranscriptionSearchResponse = {
      items:
        query === 'missing'
          ? []
          : [
              {
                id: meeting1.id,
                title: meeting1.title,
                created_datetime: meeting1.created_datetime,
                status: 'completed',
                expiring: false,
                text: '',
                no_speech_detected: false,
                matches_truncated: false,
                matches: [
                  {
                    source: 'transcript',
                    snippet,
                    snippet_start: 0,
                    highlights,
                    entry_index: 30,
                    speaker: 'Alex',
                    start_time: 300,
                    end_time: 309,
                  },
                  {
                    source: 'summary',
                    snippet,
                    snippet_start: 1_700,
                    highlights,
                    minute_id: meeting1Minutes[0].id,
                    minute_version_id: meeting1Versions[1].id,
                  },
                ],
              },
            ],
      total_count: query === 'missing' ? 0 : 21,
      total_pages: query === 'missing' ? 1 : 2,
      page: currentPage,
      page_size: 20,
    }
    const sources = params.getAll('sources')
    for (const item of response.items) {
      if (query === 'Alex Jones' && sources.includes('speaker')) {
        item.matches = [
          {
            source: 'speaker',
            snippet: 'Alex Jones',
            snippet_start: 0,
            highlights: [
              { start: 0, end: 4 },
              { start: 5, end: 10 },
            ],
            speech_excerpt: snippet,
            speaker: 'Alex Jones',
            entry_index: 30,
            start_time: 300,
            end_time: 309,
          },
        ]
      } else if (sources.length) {
        item.matches = item.matches.filter((match) =>
          sources.includes(match.source)
        )
      }
    }
    return route.fulfill(json(200, response))
  })
})

test('search renders safe bold snippets, paginates and scrolls to transcript and historical summary matches', async ({
  page,
}) => {
  await page.goto('/search')
  await expect(
    page.getByRole('heading', { name: 'Search your transcriptions' })
  ).toBeVisible()
  await page
    .getByRole('searchbox', { name: 'Search', exact: true })
    .fill('budget approval')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page).toHaveURL(/\/search\?keywords=budget\+approval$/)
  await expect(page.getByRole('heading', { name: '21 results' })).toBeVisible()
  const transcript = page.getByRole('link', { name: /Transcript at/ })
  await expect(transcript.locator('strong')).toHaveText(['budget', 'approval'])
  await expect(transcript).toContainText(
    '😀 The budget needs approval & agreement.'
  )
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])

  await page.getByRole('link', { name: 'Next page', exact: true }).click()
  await expect(page).toHaveURL(/keywords=budget\+approval&page=2$/)
  await expect(
    page.getByRole('link', { name: 'Page 2', exact: true })
  ).toHaveAttribute('aria-current', 'page')
  await transcript.click()
  await expect(page).toHaveURL(/\/transcript#search-match\?/)
  const entry = page.locator('#search-entry-30 #search-passage')
  await expect(entry).toBeFocused()
  await expect(entry).toBeInViewport()

  await page.goBack()
  await page
    .getByRole('link', { name: /View matching summary version/ })
    .click()
  await expect(page).toHaveURL(
    new RegExp(`version=${meeting1Versions[1].id}#search-match`)
  )
  const editor = page.getByRole('textbox', { name: 'Summary editor' })
  await expect(editor).not.toContainText('The newest version')
  const passage = editor.locator('p').filter({ hasText: snippet })
  await expect(passage).toBeFocused()
  await expect(passage).toBeInViewport()

  // A historical match must not be blocked by the newest version still processing.
  await page.route(
    `**/api/proxy/minutes/${meeting1Minutes[0].id}/versions`,
    (route) =>
      route.fulfill(
        json(200, [
          { ...meeting1Versions[0], status: 'in_progress', html_content: '' },
          {
            ...meeting1Versions[1],
            html_content:
              paragraphs +
              '<p>😀 The bud<strong>get</strong> needs approval &amp; agreement.</p>',
          },
        ])
      )
  )
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await expect(passage).toBeFocused()
  await expect(passage).toBeInViewport()
  await page.goto('/search?keywords=budget+approval')
  const searchButton = page.getByRole('button', { name: 'Search', exact: true })
  await expect(searchButton).toBeVisible()
  expect((await searchButton.boundingBox())!.width).toBeLessThan(60)
})

test('empty and failed searches are recoverable without changing the title search', async ({
  page,
}) => {
  expect(redactSearchUrl('https://minute.test/search?keywords=private')).toBe(
    'https://minute.test/search'
  )
  expect(
    redactSearchUrl('/transcriptions/123/transcript#search-match?text=private')
  ).toBe('/transcriptions/123/transcript')
  expect(redactSearchUrl('http://')).toBe('http://')
  const telemetry = redactSearchTelemetry({
    request: {
      url: 'https://minute.test/search?keywords=private',
      query_string: 'keywords=private',
    },
    breadcrumbs: [
      { data: { url: '/api/proxy/transcriptions/search?search=private' } },
    ],
  })
  expect(JSON.stringify(telemetry)).not.toContain('private')
  await page.goto('/search?keywords=missing')
  await expect(page.getByRole('heading', { name: '0 results' })).toBeVisible()
  await expect(
    page.getByText('No results on this page.', { exact: false })
  ).toBeVisible()
  await page
    .getByRole('searchbox', { name: 'Search', exact: true })
    .fill('error')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(
    page
      .getByRole('alert')
      .filter({ hasText: 'We could not load your search results.' })
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
  await page.goto('/transcriptions')
  await expect(
    page.getByRole('searchbox', { name: 'Search transcriptions' })
  ).toBeVisible()
})

test('source selection is submitted, retained in pagination, and speaker hits scroll to the named speaker', async ({
  page,
}) => {
  await page.goto('/search?keywords=budget+approval&page=2')
  for (const name of ['Titles', 'Transcripts', 'Summaries', 'Speakers']) {
    await expect(
      page.getByRole('checkbox', { name, exact: true })
    ).toBeChecked()
  }
  await page.getByRole('checkbox', { name: 'Speakers', exact: true }).uncheck()
  await page.getByRole('checkbox', { name: 'Titles', exact: true }).uncheck()
  await page
    .getByRole('checkbox', { name: 'Transcripts', exact: true })
    .uncheck()
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page).toHaveURL(/keywords=budget\+approval&sources=summary$/)
  await expect(page.getByRole('link', { name: /Transcript at/ })).toHaveCount(0)
  await expect(
    page.getByRole('link', { name: /View matching summary version/ })
  ).toBeVisible()
  await page.getByRole('link', { name: 'Next page', exact: true }).click()
  await expect(page).toHaveURL(/sources=summary&page=2$/)

  await page.getByRole('checkbox', { name: 'Summaries', exact: true }).uncheck()
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(
    page.getByText('Select at least one search source.', { exact: true })
  ).toBeVisible()
  await expect(page).toHaveURL(/sources=summary&page=2$/)
  await page.getByRole('checkbox', { name: 'Speakers', exact: true }).check()
  await page
    .getByRole('searchbox', { name: 'Search', exact: true })
    .fill('Alex Jones')
  const request = page.waitForRequest(
    (request) =>
      request.url().includes('/api/proxy/transcriptions/search?') &&
      new URL(request.url()).searchParams.get('search') === 'Alex Jones'
  )
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  expect(new URL((await request).url()).searchParams.getAll('sources')).toEqual(
    ['speaker']
  )
  await expect(page).toHaveURL(/keywords=Alex\+Jones&sources=speaker$/)
  const speaker = page.getByRole('link', { name: /Speaker at/ })
  await expect(speaker.locator('strong')).toHaveText(['Alex', 'Jones'])
  await expect(speaker).toContainText(snippet)
  await expect(page).toHaveTitle('Search - Minute')
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
  await speaker.click()
  await expect(page.locator('#search-speaker-30')).toBeFocused()
  await expect(page.locator('#search-speaker-30')).toBeInViewport()
})
