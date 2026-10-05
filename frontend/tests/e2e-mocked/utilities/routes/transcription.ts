import type { Page, Request } from '@playwright/test'
import type {
  MinuteListItem,
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
