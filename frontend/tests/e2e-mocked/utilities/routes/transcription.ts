import type { Page, Request } from '@playwright/test'
import type {
  MinuteListItem,
  PaginatedTranscriptionsResponse,
  TranscriptionGetResponse,
} from '@/lib/client/types.gen'
import { json } from './general'

export function waitForTranscriptPatch(page: Page): Promise<Request> {
  return page.waitForRequest(
    (request) =>
      request.method() === 'PATCH' &&
      /\/transcriptions\/[^/]+$/.test(request.url())
  )
}

export function waitForSummaryRegenerate(page: Page): Promise<Request> {
  return page.waitForRequest(
    (request) =>
      request.method() === 'POST' &&
      /\/transcription\/[^/]+\/minutes$/.test(request.url())
  )
}

export async function routeTranscription(
  page: Page,
  {
    transcription,
    minutes,
  }: {
    transcription: TranscriptionGetResponse
    minutes: MinuteListItem[]
  }
): Promise<void> {
  const transcriptionId = transcription.id

  await page.route(
    `**/api/proxy/transcriptions/${transcriptionId}`,
    (route) => {
      if (route.request().method() !== 'PATCH') return route.fallback()
      const body = route
        .request()
        .postDataJSON() as Partial<TranscriptionGetResponse>
      Object.assign(transcription, body)
      return route.fulfill(json(200, transcription))
    }
  )

  await page.route(
    `**/api/proxy/transcription/${transcriptionId}/minutes`,
    (route) => {
      if (route.request().method() !== 'POST') return route.fallback()
      return route.fulfill(json(200, minutes[0]))
    }
  )
}

/**
 * Stateful transcription list + delete routes.
 *
 * Register AFTER mockBackend(page) so these take precedence over the static
 * list route. A DELETE removes the item from a local copy of the list so the
 * row disappears when the UI invalidates and refetches.
 */
export async function routeDeleteTranscription(
  page: Page,
  { transcriptions }: { transcriptions: PaginatedTranscriptionsResponse }
): Promise<void> {
  const list: PaginatedTranscriptionsResponse = {
    ...transcriptions,
    items: [...transcriptions.items],
  }

  await page.route('**/api/proxy/transcriptions/*', (route) => {
    if (route.request().method() !== 'DELETE') return route.fallback()
    const id = new URL(route.request().url()).pathname.split('/').at(-1)
    const index = list.items.findIndex((item) => item.id === id)
    if (index !== -1) {
      list.items.splice(index, 1)
      list.total_count = Math.max(0, list.total_count - 1)
    }
    return route.fulfill(json(200, {}))
  })

  await page.route('**/api/proxy/transcriptions**', (route) => {
    const { pathname } = new URL(route.request().url())
    if (pathname !== '/api/proxy/transcriptions') return route.fallback()
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill(json(200, list))
  })
}
